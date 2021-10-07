from copy import deepcopy
from collections import defaultdict

from my_types import *


def intersects(first_start, first_end, second_start, second_end) -> bool:
    return (first_start <= second_start <= first_end) or (second_start <= first_start <= second_end)


def get_regular_meetings_from_interval(origin: Meeting, start: Timepoint, end: Timepoint):
    if not origin.period:
        return []

    meetings = []
    cur_start = origin.start
    while cur_start <= end:
        cur_end = cur_start + origin.duration()
        if intersects(cur_start, cur_end, start, end):
            cur_meeting = deepcopy(origin)
            cur_meeting.start = cur_start
            cur_meeting.end = cur_end
            meetings.append(cur_meeting)

        cur_start += origin.period

    return meetings


class WrongRequestException(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class Database:
    def __init__(self):
        super().__init__()
        self.users_by_username = dict()
        self.meetings_by_id = dict()
        # suggested meetings
        self.user_suggested_meeting_ids = defaultdict(set)
        # accepted meetings
        self.user_single_meeting_ids = defaultdict(set)
        self.user_regular_meeting_ids = defaultdict(set)
        self.currentMeetingId = 0

    def generate_new_meeting_id(self) -> MeetingId:
        id = self.currentMeetingId
        self.currentMeetingId += 1
        return id

    def add_user(self, user: User) -> User:
        self.users_by_username[user.username] = user
        return user

    def add_meeting(self, meeting: Meeting) -> Meeting:
        # check that all users are registered
        for username in {meeting.creator_username}.union(meeting.invited):
            if username not in self.users_by_username:
                raise WrongRequestException(f"No user with name {username} is registered")

        # register meeting adding creator as a participant
        meeting.id = self.generate_new_meeting_id()
        meeting.participants = set()
        meeting.participants.add(meeting.creator_username)
        meeting.invited.discard(meeting.creator_username)
        self.meetings_by_id[meeting.id] = meeting

        # add meeting to creator's accepted meetings
        meetings_storage = self.user_regular_meeting_ids if meeting.period else self.user_single_meeting_ids
        meetings_storage[meeting.creator_username].add(meeting.id)

        # add meeting to suggested list for all invited users
        for username in meeting.invited:
            self.user_suggested_meeting_ids[username].add(meeting.id)

        return meeting

    def accept_meeting(self, username: Username, meeting_id: MeetingId) -> Meeting:
        if username not in self.users_by_username:
            raise WrongRequestException(f"No user with name {username} is registered")

        if meeting_id not in self.meetings_by_id:
            raise WrongRequestException(f"No meeting with id {meeting_id} id is registered")

        if meeting_id not in self.user_suggested_meeting_ids.get(username, set()):
            raise WrongRequestException(f"User with name {username} "
                                        f"is not invited to meeting with id {meeting_id}")

        # move meeting from suggested to accepted and add user into participants
        meeting = self.meetings_by_id[meeting_id]
        meeting.invited.remove(username)
        meeting.participants.add(username)
        self.user_suggested_meeting_ids[username].remove(meeting_id)
        meetings_storage = self.user_regular_meeting_ids if meeting.period else self.user_single_meeting_ids
        meetings_storage[username].add(meeting_id)

        return meeting

    def decline_meeting(self, username: Username, meeting_id: MeetingId) -> Meeting:
        if username not in self.users_by_username:
            raise WrongRequestException(f"No user with name {username} is registered")

        if meeting_id not in self.meetings_by_id:
            raise WrongRequestException(f"No meeting with id {meeting_id} is registered")

        if meeting_id not in self.user_suggested_meeting_ids.get(username, set()):
            raise WrongRequestException(f"User with name {username} "
                                        f"is not invited to meeting with id {meeting_id}")

        # remove meeting from suggested and user from invited
        meeting = self.meetings_by_id[meeting_id]
        meeting.invited.remove(username)
        self.user_suggested_meeting_ids[username].remove(meeting_id)

        return meeting

    def get_meeting(self, meeting_id: MeetingId) -> Meeting:
        if meeting_id not in self.meetings_by_id:
            raise WrongRequestException(f"No meeting with id {meeting_id} is registered")

        return self.meetings_by_id[meeting_id]

    def get_suggested_meetings(self, username: Username) -> List[Meeting]:
        if username not in self.users_by_username:
            raise WrongRequestException(f"No user with name {username} is registered")

        return [self.meetings_by_id[meeting_id]
                for meeting_id in self.user_suggested_meeting_ids.get(username, set())]

    def get_accepted_meetings(self, username: Username, start: Timepoint, end: Timepoint) -> List[Meeting]:
        if username not in self.users_by_username:
            raise WrongRequestException(f"No user with name {username} is registered")

        regular_meetings_origins = [self.meetings_by_id[meeting_id]
                                    for meeting_id in self.user_regular_meeting_ids.get(username, set())]
        regular_meetings = sum([get_regular_meetings_from_interval(origin, start, end)
                                for origin in regular_meetings_origins], [])

        single_meetings = [self.meetings_by_id[meeting_id]
                           for meeting_id in self.user_single_meeting_ids.get(username, set())]
        single_meetings = [meeting for meeting in single_meetings
                           if intersects(meeting.start, meeting.end, start, end)]

        return single_meetings + regular_meetings

    def get_first_available_start(self, usernames: Set[Username], duration: Duration,
                                  start: Timepoint, end: Timepoint) -> Optional[Timepoint]:
        all_meetings = sum([self.get_accepted_meetings(username, start, end) for username in usernames], [])
        if len(all_meetings) == 0:
            return start

        intervals = sorted([(meeting.start, meeting.end) for meeting in all_meetings])

        last_end = start
        for cur_start, cur_end in intervals:
            if cur_start >= last_end + duration:
                return last_end
            last_end = max(last_end, cur_end)

        return None




