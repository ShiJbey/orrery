<h1 align="center">
  <img
    width="100"
    height="100"
    src="https://user-images.githubusercontent.com/11076525/211907183-33b69464-1772-4ee7-a39e-c0066ca27e91.png"
  >
<br>
Orrery: social simulation framework (WIP)
</h1>

[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Orrery is a fork of my other simulation Neighborly. This repo is basically a testbed
for more radical deviations from Neighborly's design.

The largest change between Neighborly and Orrery is the representation of physical
space. In Neighborly, characters move from one location to the next based on their
routines, tnd This movement drove relationship development. However, in Orrery,
characters between discrete locations. Instead, characters have locations that they
"frequent" based on their likes/dislikes. We then sample potential interlocutors
from the characters who overlap in their frequented locations. Relationships then
grow as a function of social rules, the amount of social overlap, and time.

Character movement was an expensive calculation in Neighborly, and it happened
every timestep. Removing this piece from the simulation has greatly helped runtime
performance, allowing Orrery to simulate 100+ years in tens of seconds versus minutes.

## Getting Started

### Installation

This package is not on PyPI yet. Until it is uploaded, please follow the directions
below. You may want to create a new virtual environment before running the
`pip install` command.

```bash
# Download the latest changes
git clone https://github.com/ShiJbey/orrery.git
# Change into the package directory
cd orrery
# Install the package to the active environment
pip install -e "."
```

### Running your first simulation

There are sample simulations available in the `samples/` directory of this project.
Each one runs a slightly different story world simulation and writes all the data
to a file for later processing.


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
            StatusDuration: {}
         }
      )


add_status(
   world,
   character,
   InDeptStatus(character.uid, loanshark.uid, 1000)
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
