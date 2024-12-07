"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, JSON, Float, BOOLEAN
from sqlalchemy.ext.declarative import declarative_base
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for local Base handling   START                                                   -   START   -
from cryptography import HashFunctions as HaFu
# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()


class UserAnonym(Base):
    """=== Classname: UserAnonym(Base) =================================================================================
    Class represents an anonym general user who's data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "useranonyms"
    email: str              = Column("email", String, primary_key=True)
    psswd_hsh: str          = Column("psswd_hsh", String)
    auth_code: int          = Column("auth_code", Integer)
    pubkey: str             = Column("pubkey", String)
    uuid: str               = Column("uuid", String)
    timestamp: float        = Column("timestamp", Float)
    disabled: bool          = Column("disabled", BOOLEAN)

    def __init__(self,
                 email: str,
                 psswd_hsh: str,
                 auth_code: int     = 0,
                 pubkey: str        = "",
                 uuid: str          = "",
                 timestamp: float   = 0.0,
                 disabled: bool     = False,
                 **kwargs):
        self.email: str         = email
        self.psswd_hsh: str     = psswd_hsh
        self.auth_code: int     = auth_code
        self.pubkey: str        = pubkey
        self.uuid: str          = uuid
        self.timestamp: float   = timestamp
        self.disabled: bool     = disabled

    def return_as_dict(self):
        """=== Method name: return_as_dict =============================================================================
        Returns instance as a dictionary
        @return : dict - parameter: argument pairs in a dict
        ========================================================================================== by Sziller ==="""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @ classmethod
    def construct(cls, d_in):
        """=== Classmethod: construct ==================================================================================
        Input necessary class parameters to instantiate object of the class!
        @param d_in: dict - format data to instantiate new object
        @return: an instance of the class
        ========================================================================================== by Sziller ==="""
        return cls(**d_in)

    def __repr__(self):
        return "user: {:<20} - added: {}".format(self.email, self.timestamp)
