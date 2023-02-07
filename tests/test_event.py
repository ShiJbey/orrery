import pytest

from orrery.core.event import Event, RoleInstance


@pytest.fixture
def sample_event():
    return Event(
        name="Price Dispute",
        timestamp="2022-01-01T00:00:00.000000",
        roles=[
            RoleInstance("Merchant", 1),
            RoleInstance("Customer", 2),
        ],
    )


@pytest.fixture
def shared_role_event():
    return Event(
        name="Declare Rivalry",
        timestamp="2022-01-01T00:00:00.000000",
        roles=[
            RoleInstance("Actor", 1),
            RoleInstance("Actor", 2),
        ],
    )


def test_life_event_get_type(sample_event: Event):
    assert sample_event.name == "Price Dispute"


def test_life_event_to_dict(sample_event: Event):
    serialized_event = sample_event.to_dict()
    assert serialized_event["name"] == "Price Dispute"
    assert serialized_event["timestamp"] == "2022-01-01T00:00:00.000000"
    assert serialized_event["roles"][0] == {"name": "Merchant", "gid": 1}
    assert serialized_event["roles"][1] == {"name": "Customer", "gid": 2}


def test_life_event_get_all(shared_role_event: Event):
    assert shared_role_event.get_all("Actor") == [1, 2]


def test_life_event_get_all_raises_key_error(shared_role_event: Event):
    with pytest.raises(KeyError):
        shared_role_event.get_all("Pizza")


def test_life_event_get_item(sample_event: Event):
    assert sample_event["Merchant"] == 1
    assert sample_event["Customer"] == 2


def test_life_event_get_item_raises_key_error(sample_event: Event):
    with pytest.raises(KeyError):
        assert sample_event["Clerk"]
