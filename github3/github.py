"""
github3.github
==============

This module contains the main GitHub session object.

"""

from requests import session
from json import dumps
from .events import Event
from .gists import Gist
from .issues import Issue, issue_params
from .legacy import LegacyIssue, LegacyRepo, LegacyUser
from .models import GitHubCore
from .orgs import Organization
from .repos import Repository
from .users import User, Key


class GitHub(GitHubCore):
    """Stores all the session information."""
    def __init__(self, login='', password=''):
        super(GitHub, self).__init__({})
        # Only accept JSON responses
        self._session.headers.update(
                {'Accept': 'application/vnd.github.full+json'})
        # Only accept UTF-8 encoded data
        self._session.headers.update({'Accept-Charset': 'utf-8'})
        # Identify who we are
        self._session.config['base_headers'].update(
                {'User-Agent': 'github3.py/pre-alpha'})
        if login and password:
            self.login(login, password)

    def __repr__(self):
        return '<GitHub at 0x{0:x}>'.format(id(self))

    def _list_follow(self, which):
        url = self._build_url('user', which)
        resp = self._get(url)
        json = self._json(resp, 200)
        return [User(f, self) for f in json]

    def authorization(self, id_num):
        """Get information about authorization ``id``.

        :param id_num: (required), unique id of the authorization
        :type id_num: int
        :returns: :class:`Authorization <Authorization>`
        """
        json = None
        if int(id_num) > 0:
            url = self._github_url('authorizations', str(id_num))
            json = self._json(self._get(url), 200)
        return Authorization(json, self) if json else None

    def authorize(self, login, password, scopes, note='', note_url=''):
        """Obtain an authorization token from the GitHub API for the GitHub
        API.

        :param login: (required)
        :type login: str
        :param password: (required)
        :type password: str
        :param scopes: (required), areas you want this token to apply to,
            i.e., 'gist', 'user'
        :type scopes: list of strings
        :param note: (optional), note about the authorization
        :returns: :class:`Authorization <Authorization>`
        """
        json = None
        auth = self._session.auth or (login and password)
        if isinstance(scopes, list) and scopes and auth:
            url = self._build_url('authorizations')
            data = dumps({'scopes': scopes, 'note': note,
                'note_url': note_url})
            if self._session.auth:
                json = self._json(self._post(url, data=data), 201)
            else:
                ses = session()
                ses.auth = (login, password)
                json = self._json(ses.post(url, data=data), 201)
        return Authorization(json, self) if json else None

    def create_gist(self, description, files, public=True):
        """Create a new gist.

        If no login was provided, it will be anonymous.

        :param description: (required), description of gist
        :type description: str
        :param files: (required), file names with associated dictionaries for
            content, e.g. ``{'spam.txt': {'content': 'File contents ...'}}``
        :type files: dict
        :param public: (optional), make the gist public if True
        :type public: bool
        :returns: :class:`Gist <github3.gist.Gist>`
        """
        new_gist = {'description': description, 'public': public,
                'files': files}
        url = self._build_url('gists')
        json = self._json(self._post(url, dumps(new_gist)), 201)
        return Gist(json, self) if json else None

    def create_issue(self,
        owner,
        repository,
        title,
        body=None,
        assignee=None,
        milestone=None,
        labels=[]):
        """Create an issue on the project 'repository' owned by 'owner'
        with title 'title'.

        body, assignee, milestone, labels are all optional.

        :param owner: (required), login of the owner
        :type owner: str
        :param repository: (required), repository name
        :type repository: str
        :param title: (required), Title of issue to be created
        :type title: str
        :param body: (optional), The text of the issue, markdown
            formatted
        :type body: str
        :param assignee: (optional), Login of person to assign
            the issue to
        :type assignee: str
        :param milestone: (optional), Which milestone to assign
            the issue to
        :type milestone: str
        :param labels: (optional), List of label names.
        :type labels: list
        :returns: :class:`Issue <github3.issue.Issue>`
        """
        repo = None
        if owner and repository and title:
            repo = self.repository(owner, repository)

        if repo:
            return repo.create_issue(title, body, assignee, milestone, labels)

        # Regardless, something went wrong. We were unable to create the
        # issue
        return None

    def create_key(self, title, key):
        """Create a new key for the authenticated user.

        :param title: (required), key title
        :type title: str
        :param key: (required), actual key contents
        :type key: str or file
        :returns: :class:`Key <github3.user.Key>`
        """
        created = None

        if title and key:
            url = self._build_url('user', 'keys')
            req = self._post(url, dumps({'title': title, 'key': key}))
            json = self._json(req, 201)
            if json:
                created = Key(json, self)
        return created

    def create_repo(self,
        name,
        description='',
        homepage='',
        private=False,
        has_issues=True,
        has_wiki=True,
        has_downloads=True):
        """Create a repository for the authenticated user.

        :param name: (required), name of the repository
        :type name: str
        :param description: (optional)
        :type description: str
        :param homepage: (optional)
        :type homepage: str
        :param private: (optional), If ``True``, create a
            private repository. API default: ``False``
        :type private: bool
        :param has_issues: (optional), If ``True``, enable
            issues for this repository. API default: ``True``
        :type has_issues: bool
        :param has_wiki: (optional), If ``True``, enable the
            wiki for this repository. API default: ``True``
        :type has_wiki: bool
        :param has_downloads: (optional), If ``True``, enable
            downloads for this repository. API default: ``True``
        :type has_downloads: bool
        :returns: :class:`Repository <github3.repo.Repository>`
        """
        url = self._build_url('user', 'repos')
        data = dumps({'name': name, 'description': description,
            'homepage': homepage, 'private': private,
            'has_issues': has_issues, 'has_wiki': has_wiki,
            'has_downloads': has_downloads})
        json = self._json(self._post(url, data), 201)
        return Repository(json, self) if json else None

    def delete_key(self, key_id):
        """Delete user key pointed to by ``key_id``.

        :param key_id: (required), unique id used by Github
        :type: int
        :returns: bool
        """
        key = self.get_key(key_id)
        if key:
            return key.delete()
        return False

    def follow(self, login):
        """Make the authenticated user follow login.

        :param login: (required), user to follow
        :type login: str
        :returns: bool
        """
        resp = False
        if login:
            url = self._build_url('user', 'following', login)
            resp = self._boolean(self._put(url), 204, 404)
        return resp

    def get_key(self, id_num):
        """Gets the authenticated user's key specified by id_num.

        :param id_num: (required), unique id of the key
        :type id_num: int
        :returns: :class:`Key <github3.user.Key>`
        """
        json = None
        if int(id_num) > 0:
            url = self._build_url('user', 'keys', str(id_num))
            json = self.json(self._get(url), 200)
        return Key(json, self) if json else None

    def gist(self, id_num):
        """Gets the gist using the specified id number.

        :param id_num: (required), unique id of the gist
        :type id_num: int
        :returns: :class:`Gist <github3.gist.Gist>`
        """
        url = self._build_url('gists', str(id_num))
        json = self._json(self._get(url), 200)
        return Gist(json, self) if json else None

    def is_following(self, login):
        """Check if the authenticated user is following login.

        :param login: (required), login of the user to check if the
            authenticated user is checking
        :type login: str
        :returns: bool
        """
        json = False
        if login:
            url = self._build_url('user', 'following', login)
            json = self._boolean(self._get(url), 204, 404)
        return json

    def is_watching(self, login, repo):
        """Check if the authenticated user is following login/repo.

        :param login: (required), owner of repository
        :type login: str
        :param repo: (required), name of repository
        :type repo: str
        :returns: bool
        """
        json = False
        if login and repo:
            url = self._build_url('user', 'watched', login, repo)
            json = self._boolean(self._get(url), 204, 404)
        return json

    def issue(self, owner, repository, number):
        """Fetch issue #:number: from https://github.com/:owner:/:repository:

        :param owner: (required), owner of the repository
        :type owner: str
        :param repository: (required), name of the repository
        :type repository: str
        :param number: (required), issue number
        :type number: int
        :return: :class:`Issue <github3.issue.Issue>`
        """
        repo = self.repository(owner, repository)
        if repo:
            return repo.issue(number)
        return None

    def list_authorizations(self):
        """List authorizations for the authenticated user.

        :returns: list of :class:`Authorization <Authorization>`\ s
        """
        url = self._build_url('authorizations')
        json = self._json(self._get(url), 200)
        return [Authorization(a, self) for a in json]

    def list_emails(self):
        """List email addresses for the authenticated user.

        :returns: list of dicts
        """
        url = self._build_url('user', 'emails')
        req = self._get(url)
        return self._json(req, 200) or []

    def list_events(self):
        """List public events.

        :returns: list of :class:`Event <github3.event.Event>`\ s
        """
        url = self._build_url('events')
        json = self._json(self._get(url), 200)
        return [Event(ev, self) for ev in json]

    def list_followers(self, login=None):
        """If login is provided, return a list of followers of that
        login name; otherwise return a list of followers of the
        authenticated user.

        :param login: (optional), login of the user to check
        :type login: str
        :returns: list of :class:`User <github3.user.User>`\ s
        """
        if login:
            return self.user(login).list_followers()
        return self._list_follow('followers')

    def list_following(self, login=None):
        """If login is provided, return a list of users being followed
        by login; otherwise return a list of people followed by the
        authenticated user.

        :param login: (optional), login of the user to check
        :type login: str
        :returns: list of :class:`User <github3.user.User>`\ s
        """
        if login:
            return self.user(login).list_following()
        return self._list_follow('following')

    def list_gists(self, username=None):
        """If no username is specified, GET /gists, otherwise GET
        /users/:username/gists

        :param login: (optional), login of the user to check
        :type login: str
        :returns: list of :class:`Gist <github3.gist.Gist>`\ s
        """
        if username:
            url = self._build_url('users', username, 'gists')
        else:
            url = self._build_url('gists')
        json = self._json(self._get(url), 200)
        return [Gist(gist, self) for gist in json]

    @GitHubCore.requires_auth
    def list_user_issues(self, filter='', state='', labels='', sort='',
        direction='', since=''):
        """List the authenticated user's issues.

        :param str filter: accepted values:
            ('assigned', 'created', 'mentioned', 'subscribed')
            api-default: 'assigned'
        :param str state: accepted values: ('open', 'closed')
            api-default: 'open'
        :param str labels: comma-separated list of label names, e.g.,
            'bug,ui,@high'
        :param str sort: accepted values: ('created', 'updated', 'comments')
            api-default: created
        :param str direction: accepted values: ('asc', 'desc')
            api-default: desc
        :param str since: ISO 8601 formatted timestamp, e.g.,
            2012-05-20T23:10:27Z
        """
        url = self._build_url('issues')
        params = issue_params(filter, state, labels, sort, direction,
                since)
        json = self._json(self._get(url, params=params), 200)
        return [Issue(issue, self) for issue in json]

    def list_repo_issues(self, owner, repository, milestone=None,
        state='', assignee='', mentioned='', labels='', sort='', direction='',
        since=''):
        """List issues on owner/repository. Only owner and repository are
        required.

        :param str owner: login of the owner of the repository
        :param str repository: name of the repository
        :param int milestone: None, '*', or ID of milestone
        :param str state: accepted values: ('open', 'closed')
            api-default: 'open'
        :param str assignee: '*' or login of the user
        :param str mentioned: login of the user
        :param str labels: comma-separated list of label names, e.g.,
            'bug,ui,@high'
        :param str sort: accepted values: ('created', 'updated', 'comments')
            api-default: created
        :param str direction: accepted values: ('asc', 'desc')
            api-default: desc
        :param str since: ISO 8601 formatted timestamp, e.g.,
            2012-05-20T23:10:27Z
        :returns: list of :class:`Issue <github3.issue.Issue>`\ s
        """
        issues = None
        if owner and repository:
            repo = self.repository(owner, repository)
            issues = repo.list_issues(milestone, state, assignee, mentioned,
                    labels, direction, since)
        return issues

    def list_keys(self):
        """List public keys for the authenticated user.

        :returns: list of :class:`Key <github3.user.Key>`\ s
        """
        url = self._build_url('user', 'keys')
        json = self._json(self._get(url), 200)
        return [Key(key, self) for key in json]

    def list_orgs(self, login=None):
        """List public organizations for login if provided; otherwise
        list public and private organizations for the authenticated
        user.

        :param login: (optional), user whose orgs you wish to list
        :type login: str
        :returns: list of :class:`Organization <github3.org.Organization>`\ s
        """
        if login:
            url = self._build_url('users', login, 'orgs')
        else:
            url = self._build_url('usr', 'orgs')

        json = self._json(self._get(url), 200)
        return [Organization(org, self) for org in json]

    def list_repos(self, login=None, type='', sort='', direction=''):
        """List public repositories for the specified ``login`` or all
        repositories for the authenticated user if ``login`` is not
        provided.

        :param login: (optional)
        :type login: str
        :param type: (optional), accepted values:
            ('all', 'owner', 'public', 'private', 'member')
            API default: 'all'
        :type type: str
        :param sort: (optional), accepted values:
            ('created', 'updated', 'pushed', 'full_name')
            API default: 'created'
        :type sort: str
        :param direction: (optional), accepted values:
            ('asc', 'desc'), API default: 'asc' when using 'full_name',
            'desc' otherwise
        :type direction: str
        :returns: list of :class:`Repository <github3.repo.Repository>`
            objects
        """
        if login:
            url = self._build_url('users', login, 'repos')
        else:
            url = self._build_url('user', 'repos')

        params = {}
        if type in ('all', 'owner', 'public', 'private', 'member'):
            params.update(type=type)
        if not login:
            if sort in ('created', 'updated', 'pushed', 'full_name'):
                params.update(sort=sort)
            if direction in ('asc', 'desc'):
                params.update(direction=direction)

        json = self._json(self._get(url, params=params), 200)
        return [Repository(repo, self) for repo in json]

    def list_watching(self, login=None):
        """List the repositories being watched by ``login`` if provided or the
        repositories being watched by the authenticated user.

        :param login: (optional)
        :type login: str
        :returns: list of :class:`Repository <github3.repo.Repository>`
            objects
        """
        if login:
            url = self._build_url('users', login, 'watched')
        else:
            url = self._build_url('user', 'watched')
        json = self._json(self._get(url), 200)
        return [Repository(repo, self) for repo in json]

    def login(self, username=None, password=None, token=None):
        """Logs the user into GitHub for protected API calls.

        :param username: (optional)
        :type username: str
        :param password: (optional)
        :type password: str
        :param token: (optional)
        :type token: str
        """
        if username and password:
            self._session.auth = (username, password)
        elif token:
            self._session.headers.update({
                'Authorization': 'token ' + token
                })

    def markdown(self, text, mode='', context='', raw=False):
        """Render an arbitrary markdown document.

        :param text: (required), the text of the document to render
        :type text: str
        :param mode: (optional), 'markdown' or 'gfm'
        :type mode: str
        :param context: (optional), only important when using mode 'gfm',
            this is the repository to use as the context for the rendering
        :type context: str
        :param raw: (optional), renders a document like a README.md, no gfm, no
            context
        :type raw: bool
        :returns: str -- HTML formatted text
        """
        data = None
        headers = {}
        if raw:
            url = self._build_url('markdown', 'raw')
            data = text
            headers['content-type'] = 'text/plain'
        else:
            url = self._build_url('markdown')
            data = {}

            if text:
                data['text'] = text

            if mode in ('markdown', 'gfm'):
                data['mode'] = mode

            if context:
                data['context'] = context

            data = dumps(data)

        if data:
            req = self._post(url, data=data, headers=headers)
            if req.ok:
                return req.content
        return ''

    def organization(self, login):
        """Returns a Organization object for the login name

        :param login: (required), login name of the org
        :type login: str
        :returns: :class:`Organization <github3.org.Organization>`
        """
        url = self._build_url('orgs', login)
        json = self._json(self._get(url), 200)
        return Organization(json, self) if json else None

    def repository(self, owner, repository):
        """Returns a Repository object for the specified combination of
        owner and repository

        :param owner: (required)
        :type owner: str
        :param repository: (required)
        :type repository: str
        :returns: :class:`Repository <github3.repo.Repository>`
        """
        url = self._build_url('repos', owner, repository)
        json = self._json(self._get(url), 200)
        return Repository(json, self) if json else None

    def search_issues(self, owner, repo, state, keyword):
        """Find issues by state and keyword.

        :param owner: (required)
        :type owner: str
        :param repo: (required)
        :type repo: str
        :param state: (required), accepted values: ('open', 'closed')
        :type state: str
        :param keyword: (required), what to search for
        :type keyword: str
        :returns: list of :class:`LegacyIssue <github3.legacy.LegacyIssue>`\ s
        """
        url = self._build_url('legacy', 'issues', 'search', owner, repo,
                state, keyword)
        json = self._json(self._get(url), 200)
        issues = json.get('issues', [])
        return [LegacyIssue(l, self) for l in issues]

    def search_repos(self, keyword, **params):
        """Search all repositories by keyword.

        :param keyword: (required)
        :type keyword: str
        :param params: (optional), filter by language and/or start_page
        :type params: dict
        :returns: list of :class:`LegacyRepo <github3.legacy.LegacyRepo>`\ s
        """
        url = self._build_url('legacy', 'repos', 'search', keyword)
        json = self._json(self._get(url, params=params), 200)
        repos = json.get('repositories', [])
        return [LegacyRepo(r, self) for r in repos]

    def search_users(self, keyword):
        """Search all users by keyword.

        :param keyword: (required)
        :type keyword: str
        :returns: list of :class:`LegacyUser <github3.legacy.LegacyUser>`\ s
        """
        url = self._github_url + '/legacy/user/search/{0}'.format(keyword)
        json = self._json(self._get(url), 200)
        users = json.get('users', [])
        return [LegacyUser(u, self) for u in users]

    def search_email(self, email):
        """Search users by email.

        :param email: (required)
        :type keyword: str
        :returns: :class:`LegacyUser <github3.legacy.LegacyUser>`
        """
        url = self._build_url('legacy', 'user', 'email', email)
        json = self._json(self._get(url), 200)
        u = json.get('user', {})
        return LegacyUser(u, self) if u else None

    def unfollow(self, login):
        """Make the authenticated user stop following login

        :param login: (required)
        :type login: str
        :returns: bool
        """
        resp = False
        if login:
            url = self._build_url('user', 'following', login)
            resp = self._boolean(self._delete(url), 204, 404)
        return resp

    def update_user(self, name=None, email=None, blog=None,
            company=None, location=None, hireable=False, bio=None):
        """If authenticated as this user, update the information with
        the information provided in the parameters. All parameters are
        optional.

        :param name: e.g., 'John Smith', not login name
        :type name: str
        :param email: e.g., 'john.smith@example.com'
        :type email: str
        :param blog: e.g., 'http://www.example.com/jsmith/blog'
        :type blog: str
        :param company: company name
        :type company: str
        :param location: where you are located
        :type location: str
        :param hireable: defaults to False
        :type hireable: bool
        :param bio: GitHub flavored markdown
        :type bio: str
        :returns: bool
        """
        user = self.user()
        if user:
            return user.update(name, email, blog, company, location, hireable,
                    bio)
        return False

    def user(self, login=None):
        """Returns a User object for the specified login name if
        provided. If no login name is provided, this will return a User
        object for the authenticated user.

        :param login: (optional)
        :type login: str
        :returns: :class:`User <github3.user.User>`
        """
        if login:
            url = self._build_url('users', login)
        else:
            url = self._build_url('user')

        json = self._json(self._get(url), 200)
        return User(json, self._session) if json else None

    def watch(self, login, repo):
        """Make user start watching login/repo.

        :param login: (required), owner of repository
        :type login: str
        :param repo: (required), name of repository
        :type repo: str
        :returns: bool
        """
        resp = False
        if login and repo:
            url = self._build_url('user', 'watched', login, repo)
            resp = self._boolean(self._put(url), 204, 404)
        return resp

    def unwatch(self, login, repo):
        """Make user stop watching login/repo.

        :param login: (required), owner of repository
        :type login: str
        :param repo: (required), name of repository
        :type repo: str
        :returns: bool
        """
        resp = False
        if login and repo:
            url = self._build_url('user', 'watched', login, repo)
            resp = self._boolean(self._delete(url), 204, 404)
        return resp


class Authorization(GitHubCore):
    """The :class:`Authorization <Authorization>` object."""
    def __init__(self, auth, session):
        super(Authorization, self).__init__(auth, session)
        self._update_(auth)

    def __repr__(self):
        return '<Authorization [{0}]>'.format(self._app.get('name', ''))

    def _update_(self, auth):
        self._app = auth.get('app', {})
        self._token = auth.get('token', '')
        self._note_url = auth.get('note_url', '')
        self._note = auth.get('note', '')
        self._scopes = auth.get('scopes', [])
        self._id = auth.get('id', 0)
        self._api = self._build_url('authorizations', str(self._id))
        self._created = None
        if auth.get('created_at'):
            self._created = self._strptime(auth.get('created_at'))
        self._updated = None
        if auth.get('updated_at'):
            self._updated = self._strptime(auth.get('updated_at'))

    @property
    def app(self):
        """Details about the application"""
        return self._app

    @property
    def created_at(self):
        """datetime object representing when the authorization was created."""
        return self._created

    def delete(self):
        """delete this authorization"""
        return self._boolean(self._delete(self._api), 204, 404)

    @property
    def id(self):
        """Unique id of the authorization"""
        return self._id

    @property
    def note(self):
        """Note about the authorization"""
        return self._note

    @property
    def note_url(self):
        """URL about the note"""
        return self._note_url

    @property
    def scopes(self):
        """List of scopes this applies to"""
        return self._scopes

    @property
    def token(self):
        """Returns the Authorization token"""
        return self._token

    def update(self, scopes=[], add_scopes=[], rm_scopes=[], note='',
            note_url=''):
        """Update this authorization.

        :param scopes: (optional), replaces the authorization scopes with these
        :type scopes: list
        :param add_scopes: (optional), scopes to be added
        :type add_scopes: list
        :param rm_scopes: (optional), scopes to be removed
        :type rm_scopes: list
        :param note: (optional), new note about authorization
        :type note: str
        :param note_url: (optional), new note URL about this authorization
        :type note_url: str
        :returns: bool
        """
        success = False
        if scopes:
            d = dumps({'scopes': scopes})
            json = self._json(self._get(self._api, data=d), 200)
            self._update_(json)
            success = True
        if add_scopes:
            d = dumps({'add_scopes': add_scopes})
            json = self._json(self._get(self._api, data=d), 200)
            self._update_(json)
            success = True
        if rm_scopes:
            d = dumps({'remove_scopes': rm_scopes})
            json = self._json(self._get(self._api, data=d), 200)
            self._update_(json)
            success = True
        if note or note_url:
            d = dumps({'note': note, 'note_url': note_url})
            json = self._json(self._get(self._api, data=d), 200)
            self._update_(json)
            success = True
        return success

    @property
    def updated_at(self):
        """datetime object representing when the authorization was created."""
        return self._updated
