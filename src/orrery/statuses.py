from __future__ import annotations

from typing import Any, Dict, List

from orrery import events
from orrery.components.business import Occupation
from orrery.components.character import Departed, GameCharacter
from orrery.components.residence import Resident
from orrery.components.shared import Active
from orrery.core.ecs import GameObject, World
from orrery.core.event import EventHandler
from orrery.core.relationship import RelationshipManager, RelationshipTag
from orrery.core.status import Status
from orrery.core.time import SimDateTime, TimeDelta
from orrery.utils.common import (
    check_share_residence,
    create_character,
    generate_child_bundle,
    set_residence,
)
from orrery.utils.relationships import add_relationship
from orrery.utils.statuses import remove_status


class Unemployed(Status):
    """
    Status component that marks a character as being able to work but lacking a job

    Attributes
    ----------
    days_to_find_a_job: int
        The number of remaining days to find a job
    grace_period: int
        The starting number of days to find a job
    """

    __slots__ = "days_to_find_a_job", "grace_period"

    def __init__(self, days_to_find_a_job: int) -> None:
        super(Status, self).__init__()
        self.days_to_find_a_job: int = days_to_find_a_job
        self.grace_period: int = days_to_find_a_job

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "days_to_find_a_job": self.days_to_find_a_job,
            "grace_period": self.grace_period,
        }

    def on_update(
        self, world: World, owner: GameObject, elapsed_time: TimeDelta
    ) -> None:
        self.days_to_find_a_job -= elapsed_time.total_days

        if self.days_to_find_a_job <= 0:
            spouses = owner.get_component(RelationshipManager).get_all_with_tags(
                RelationshipTag.Spouse
            )

            # Do not depart if one or more of the entity's spouses has a job
            if any(
                [
                    world.get_gameobject(rel.target).has_component(Occupation)
                    for rel in spouses
                ]
            ):
                return

            else:
                characters_to_depart: List[GameObject] = [owner]

                # Have all spouses depart
                # Allows for polygamy
                for rel in spouses:
                    spouse = world.get_gameobject(rel.target)
                    if spouse.has_component(Active):
                        characters_to_depart.append(spouse)

                # Have all children living in the same house depart
                children = owner.get_component(RelationshipManager).get_all_with_tags(
                    RelationshipTag.Child
                )
                for rel in children:
                    child = world.get_gameobject(rel.target)
                    if child.has_component(Active) and check_share_residence(
                        owner, child
                    ):
                        characters_to_depart.append(child)

                for c in characters_to_depart:
                    c.add_component(Departed())
                    c.remove_component(Active, immediate=True)

                remove_status(owner, Unemployed)

                event = events.DepartEvent(
                    world.get_resource(SimDateTime),
                    characters_to_depart,
                    "unemployment",
                )

                world.get_resource(EventHandler).record_event(event)


class Pregnant(Status):
    """
    Pregnant characters give birth to new child characters after the due_date

    Attributes
    ----------
    partner_id: int
        The GameObject ID of the character that impregnated this character
    due_date: SimDateTime
        The date that the baby is due
    """

    __slots__ = "partner_id", "due_date"

    def __init__(self, partner_id: int, due_date: SimDateTime) -> None:
        super(Status, self).__init__()
        self.partner_id: int = partner_id
        self.due_date: SimDateTime = due_date

    def on_update(
        self, world: World, owner: GameObject, elapsed_time: TimeDelta
    ) -> None:
        current_date = world.get_resource(SimDateTime)

        if self.due_date <= current_date:
            return

        other_parent = world.get_gameobject(self.partner_id)

        baby = create_character(
            world,
            generate_child_bundle(
                world,
                owner,
                other_parent,
            ),
            last_name=owner.get_component(GameCharacter).last_name,
        )

        set_residence(
            world,
            baby,
            world.get_gameobject(owner.get_component(Resident).residence),
        )

        # Birthing parent to child
        add_relationship(owner, baby)
        owner.get_component(RelationshipManager).get(baby.uid).add_tags(
            RelationshipTag.Child
        )

        # Child to birthing parent
        add_relationship(baby, owner)
        baby.get_component(RelationshipManager).get(owner.uid).add_tags(
            RelationshipTag.Parent
        )

        # Other parent to child
        add_relationship(other_parent, baby)
        other_parent.get_component(RelationshipManager).get(baby.uid).add_tags(
            RelationshipTag.Child
        )
        other_parent.get_component(RelationshipManager).get(baby.uid).add_tags(
            RelationshipTag.Family
        )

        # Child to other parent
        add_relationship(baby, other_parent)
        baby.get_component(RelationshipManager).get(other_parent.uid).add_tags(
            RelationshipTag.Parent
        )
        baby.get_component(RelationshipManager).get(other_parent.uid).add_tags(
            RelationshipTag.Family
        )

        # Create relationships with children of birthing parent
        for rel in owner.get_component(RelationshipManager).get_all_with_tags(
            RelationshipTag.Child
        ):
            if rel.target == baby.uid:
                continue

            sibling = world.get_gameobject(rel.target)

            # Baby to sibling
            add_relationship(baby, sibling)
            baby.get_component(RelationshipManager).get(rel.target).add_tags(
                RelationshipTag.Sibling
            )
            baby.get_component(RelationshipManager).get(rel.target).add_tags(
                RelationshipTag.Family
            )

            # Sibling to baby
            add_relationship(sibling, baby)
            world.get_gameobject(rel.target).get_component(RelationshipManager).get(
                baby.uid
            ).add_tags(RelationshipTag.Sibling)
            world.get_gameobject(rel.target).get_component(RelationshipManager).get(
                baby.uid
            ).add_tags(RelationshipTag.Family)

        # Create relationships with children of other parent
        for rel in other_parent.get_component(RelationshipManager).get_all_with_tags(
            RelationshipTag.Child
        ):
            if rel.target == baby.uid:
                continue

            sibling = world.get_gameobject(rel.target)

            # Baby to sibling
            add_relationship(baby, sibling)
            baby.get_component(RelationshipManager).get(rel.target).add_tags(
                RelationshipTag.Sibling
            )

            # Sibling to baby
            add_relationship(sibling, baby)
            sibling.get_component(RelationshipManager).get(baby.uid).add_tags(
                RelationshipTag.Sibling
            )

        remove_status(owner, Pregnant)

        # Pregnancy event dates are retro-fit to be the actual date that the
        # child was due.
        world.get_resource(EventHandler).record_event(
            events.ChildBirthEvent(current_date, owner, other_parent, baby)
        )
