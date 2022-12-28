# Orrery: social simulation framework

[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

## Getting Started

```commandline
pip install orrery
```

## Frequently Asked Questions

### How are relationships represented?

Relationships are represented as a collection of stats that correspond to
various social concepts like friendship, romance, trust, and power. Users
can specify what relationship stats are tracked between characters.

For now, relationships are only maintained between characters and not
between characters and inanimate objects like buildings.

#### Defining the relationship schema

The structure of relationships is specified using a relationship schema.
The purpose of the relationship schema is to tell the simulation how to
construct each stat within a relationship. An example schema is given
below.

```yaml
# ... (other configuration settings)
# ...
# Each stat is a sub-object under RelationshipSchema
RelationshipSchema:
    Friendship:
        # Integer value
        max: 100
        # Integer value <= max
        min: -100
        # Specifies if the stat grows as a function of interaction
        changes_with_time: true
    Romance:
        max: 100
        min: -100
        changes_with_time: true
    # Additional stats
```

#### Alternative way to representing relationships

Not social connections can be adequately represented using
the relationship system shown above. For example, if someone
wanted to represent a character owing debt to another, that
may not be something that you want to include in the schema.

An alternative may be to use the Status system to represent
being in debt. Example code is given below for how someone
would do this. Note that we create a subclass of component
bundle to handle simplify creating more of these status
type.

One of the benefits of representing relationships like this
is injecting custom components into the mix and using them
when querying for certain types of relationships

```python
@dataclass
class RelationshipStatus:
    owner: int
    target: int

@dataclass
class StatusDuration:
    duration: int = -1
    elapsed: int = 0

@dataclass
class InDebt:
    amount: int


class InDeptStatus(ComponentBundle):

    def __init__(self, owner: int, target: int, amount: int) -> None:
        super().__init__(
            {
                RelationshipStatus: {
                    "owner": owner,
                    "target": target,
                },
                InDebt: {
                    "amount": amount
                },
                StatusDuration {}
            }
        )

add_status(
    world,
    character,
    InDeptStatus(character.id, loanshark.id, 1000)
)
```

### How do relationships change over time?

Relationships in Orrery naturally evolve as a function of the current
strength of the stat and the interaction score of the relationship.

The interaction score is a measure of how likely two characters are
to interact over a long period of time. Factors that affect the
interaction score are characters living together, working at the same
business, or frequenting the same locations.

The interaction score is valued from 0 to 5 and the stronger the score
the faster the relationship grows.

### How is the interaction score affected?

1. Each character has a set of locations that they frequent based on
   their current state in the simulation. For example, children frequent
   a specific school and their home, and adults frequent their jobs, homes,
   and other businesses. Characters start new relationships by randomly
   meeting other characters who frequent the same locations. These new
   interactions increase character's interaction scores, allowing a new
   relationship to evolve between then and the other character. This score
   remains even if characters no longer frequent the location. We write this
   off as characters staying in touch.
2. Starting a new job, moving into a residence, leaving a job, dying, or leaving
   the simulation entirely, are all events that may increase or decrease
   characters' interaction scores.
