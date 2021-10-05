import datetime
from typing import List, Dict, Set, Optional
from pydantic import BaseModel
from copy import deepcopy
from collections import defaultdict

UserId = int
MeetingId = int
Timepoint = datetime.datetime
Duration = datetime.timedelta


class User(BaseModel):
    id: Optional[UserId] = None
    name: str


class Meeting(BaseModel):
    id: Optional[MeetingId] = None
    start: Timepoint
    end: Timepoint
    creator_id: UserId
    invited: Set[UserId]
    participants: Optional[Set[UserId]] = set()
    period: Optional[Duration] = None

    def duration(self) -> Duration:
        return self.end - self.start


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


class Database(BaseModel):
    users_by_id: Dict[UserId, User] = dict()
    meetings_by_id: Dict[MeetingId, Meeting] = dict()
    # suggested meetings
    user_suggested_meetings: defaultdict[UserId, Set[MeetingId]] = defaultdict(set)

    # accepted meetings
    user_single_meetings: defaultdict[UserId, Set[MeetingId]] = defaultdict(set)
    user_regular_meetings: defaultdict[UserId, Set[MeetingId]] = defaultdict(set)

    currentUserId: UserId = 0
    currentMeetingId: MeetingId = 0

    def __init__(self):
        super().__init__()
        self.users_by_id = dict()
        self.meetings_by_id = dict()
        self.user_suggested_meetings = defaultdict(set)
        self.user_single_meetings = defaultdict(set)
        self.user_regular_meetings = defaultdict(set)
        self.currentUserId = 0
        self.currentMeetingId = 0

    def generate_new_user_id(self) -> UserId:
        id = self.currentUserId
        self.currentUserId += 1
        return id

    def generate_new_meeting_id(self) -> MeetingId:
        id = self.currentMeetingId
        self.currentMeetingId += 1
        return id

    def add_user(self, user: User) -> User:
        user.id = self.generate_new_user_id()
        self.users_by_id[user.id] = user
        return user

    def add_meeting(self, meeting: Meeting) -> Meeting:
        # check that all users are registered
        for user_id in {meeting.creator_id}.union(meeting.invited):
            if user_id not in self.users_by_id:
                raise WrongRequestException(f"No user with id {user_id} is registered")

        # register meeting adding creator as a participant
        meeting.id = self.generate_new_meeting_id()
        meeting.participants = set()
        meeting.participants.add(meeting.creator_id)
        meeting.invited.discard(meeting.creator_id)
        self.meetings_by_id[meeting.id] = meeting

        # add meeting to creator's accepted meetings
        meetings_storage = self.user_regular_meetings if meeting.period else self.user_single_meetings
        meetings_storage[meeting.creator_id].add(meeting.id)

        # add meeting to suggested list for all invited users
        for user_id in meeting.invited:
            self.user_suggested_meetings[user_id].add(meeting.id)

        return meeting

    def accept_meeting(self, user_id: UserId, meeting_id: MeetingId) -> Meeting:
        if user_id not in self.users_by_id:
            raise WrongRequestException(f"No user with id {user_id} is registered")

        if meeting_id not in self.meetings_by_id:
            raise WrongRequestException(f"No meeting with id {meeting_id} id is registered")

        if meeting_id not in self.user_suggested_meetings.get(user_id, set()):
            raise WrongRequestException(f"User with id {user_id} "
                                        f"is not invited to meeting with id {meeting_id}")

        # move meeting from suggested to accepted and add user into participants
        meeting = self.meetings_by_id[meeting_id]
        meeting.invited.remove(user_id)
        meeting.participants.add(user_id)
        self.user_suggested_meetings[user_id].remove(meeting_id)
        meetings_storage = self.user_regular_meetings if meeting.period else self.user_single_meetings
        meetings_storage[user_id].add(meeting_id)

        return meeting

    def decline_meeting(self, user_id: UserId, meeting_id: MeetingId) -> Meeting:
        if user_id not in self.users_by_id:
            raise WrongRequestException(f"No user with {user_id} id is registered")

        if meeting_id not in self.meetings_by_id:
            raise WrongRequestException(f"No meeting with {meeting_id} id is registered")

        if meeting_id not in self.user_suggested_meetings.get(user_id, set()):
            raise WrongRequestException(f"User with {user_id} id "
                                        f"is not invited to meeting with {meeting_id} id")

        # remove meeting from suggested
        meeting = self.meetings_by_id[meeting_id]
        meeting.invited.remove(user_id)
        self.user_suggested_meetings[user_id].remove(meeting_id)

        return meeting

    def get_meeting(self, meeting_id: MeetingId) -> Meeting:
        if meeting_id not in self.meetings_by_id:
            raise WrongRequestException(f"No meeting with id {meeting_id} is registered")

        return self.meetings_by_id[meeting_id]

    """
    returns all meetings to which user with user_id is invited
    """
    def get_suggested_meetings(self, user_id: UserId) -> List[Meeting]:
        if user_id not in self.users_by_id:
            raise WrongRequestException(f"No user with {user_id} is registered")

        return [self.meetings_by_id[meeting_id]
                for meeting_id in self.user_suggested_meetings.get(user_id, set())]

    def get_accepted_meetings(self, user_id: UserId, start: Timepoint, end: Timepoint) -> List[Meeting]:
        if user_id not in self.users_by_id:
            raise WrongRequestException(f"No user with {user_id} is registered")

        regular_meetings_origins = [self.meetings_by_id[meeting_id]
                                   for meeting_id in self.user_regular_meetings.get(user_id, set())]
        regular_meetings = sum([get_regular_meetings_from_interval(origin, start, end)
                                for origin in regular_meetings_origins], [])

        single_meetings = [self.meetings_by_id[meeting_id]
                           for meeting_id in self.user_single_meetings.get(user_id, set())]
        single_meetings = [meeting for meeting in single_meetings
                           if intersects(meeting.start, meeting.end, start, end)]

        return single_meetings + regular_meetings

    def get_first_available_start(self, user_ids: Set[UserId], duration: Duration,
                                  start: Timepoint, end: Timepoint) -> Optional[Timepoint]:
        all_meetings = sum([self.get_accepted_meetings(user_id, start, end) for user_id in user_ids], [])
        intervals = sorted([(meeting.start, meeting.end) for meeting in all_meetings])

        last_end = start
        for cur_start, cur_end in intervals:
            if cur_start >= last_end + duration:
                return last_end
            last_end = max(last_end, cur_end)

        return None




