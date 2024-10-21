"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for local Base handling   START                                                   -   START   -
import random as rnd
# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()

class MDPrvKey(Base):
    """=== Class name: MDPrvKey ========================================================================================
    Table row.
    ============================================================================================== by Sziller ==="""
    __tablename__ = "mdprvkeys"
    hxstr: str = Column("hxstr", String, primary_key=True)
    owner: str = Column("owner", String)
    kind: int = Column("kind", Integer)
    comment: str = Column("comment", String)
    root_hxstr: str = Column("root_hxstr", String)
    deriv_nr: int = Column("deriv_nr", Integer)

    def __init__(self,
                 owner: str,
                 kind: int = 0,
                 root_hxstr: str = "",
                 deriv_nr: int = 0,
                 hxstr: str = "",
                 comment: str = "some txt"):
        self.hxstr: str = hxstr
        self.owner: str = owner
        self.kind: int = kind
        self.comment: str = comment
        self.root_hxstr: str = root_hxstr
        self.deriv_nr: int = deriv_nr

        if not self.hxstr:
            self.generate_hxstr()

    def generate_hxstr(self):
        """Function adds a unique ID <hxstr> to the row"""
        self.hxstr = "{:04}".format(rnd.randint(0, 9999))

    def return_as_dict(self):
        """=== Method name: return_as_dict =============================================================================
        Returns instance as a dictionary
        @return : dict - parameter: argument pairs in a dict
        ========================================================================================== by Sziller ==="""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in):
        """=== Classmethod: construct ==================================================================================
        Input necessary class parameters to instantiate object of the class!
        @param d_in: dict - format data to instantiate new object
        @return: an instance of the class
        ========================================================================================== by Sziller ==="""
        return cls(**d_in)
