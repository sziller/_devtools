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


class User(Base):
    """=== Classname: User(Base) =======================================================================================
    Class represents general user who's data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "users"
    username: str           = Column("username", String, primary_key=True)
    psswd_hsh: str          = Column("psswd_hsh", String)
    email: str              = Column("email", String, unique=True)
    usr_fn: str             = Column("usr_fn", String)
    usr_ln: str             = Column("usr_ln", String)
    auth_code: int          = Column("auth_code", Integer)
    pubkey: str             = Column("pubkey", String)
    email_arch: list        = Column("email_arch", JSON)
    uuid: str               = Column("uuid", String)
    timestamp: float        = Column("timestamp", Float)
    disabled: bool          = Column("disabled", BOOLEAN)

    def __init__(self,
                 username: str,
                 psswd_hsh: str,
                 email: str,
                 usr_fn: str        = "",
                 usr_ln: str        = "",
                 auth_code: int     = 0,
                 pubkey: str        = "",
                 email_arch: list   = [],
                 uuid: str          = "",
                 timestamp: float   = 0.0,
                 disabled: bool     = False,
                 **kwargs):
        self.username: str      = username
        self.psswd_hsh: str     = psswd_hsh
        self.email: str         = email
        self.usr_fn: str        = usr_fn
        self.usr_ln: str        = usr_ln
        self.auth_code: int     = auth_code
        self.pubkey: str        = pubkey
        self.email_arch: list   = email_arch
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
        return "user: {:<20} - {:<35} called: {:<15}, {:<15} - added: {}".format(self.username,
                                                                                 self.email,
                                                                                 self.usr_ln,
                                                                                 self.usr_fn,
                                                                                 self.timestamp)
