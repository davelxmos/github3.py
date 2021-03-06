import base
from expecter import expect
from github3.events import Event
from github3.orgs import Organization


class TestEvent(base.BaseTest):
    def __test_events(self, events):
        expect(events) != []
        for e in events:
            self.assertAreNotNone(e, 'actor', 'created_at', 'id', 'repo',
                    'type')
            if e.org:
                expect(e.org).isinstance(Organization)
            expect(e.payload).isinstance(dict)
            expect(e.is_public()).isinstance(bool)
            expect(e.to_json()).isinstance(dict)
            expect(e.repo).isinstance(tuple)

    def test_events(self):
        expect(Event.list_types()) != []

        events = self.g.list_events()
        self.__test_events(events)

        if self.auth:
            user = self._g.user()
            for public in (True, False):
                events = user.list_events(public)
                self.__test_events(events)
