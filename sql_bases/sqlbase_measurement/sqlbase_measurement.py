"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for local Base handling   START                                                   -   START   -
import time
from cryptography import HashFunctions as HaFu
# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()


class Measurement(Base):
    """=== Classname: Record(Base) =====================================================================================
    Class represents general record who's data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "measurements"
    mea_hash: str = Column("mea_hash", String, primary_key=True)
    mea_type: str = Column("mea_type", String)
    mea_loc: str = Column("mea_loc", String)
    mea_val: float = Column("mea_val", Float)
    mea_dim: str = Column("mea_dim", String)
    mea_time: str = Column("mea_time", String)
    timestamp: float = Column("timestamp", Integer)

    def __init__(self,
                 mea_type: str,
                 mea_loc: str,
                 mea_val: float,
                 mea_dim: str,
                 mea_time: str,
                 timestamp: int = 0
                 ):
        self.mea_hash: str = self.generate_id_hash()
        self.mea_type: str = mea_type
        self.mea_loc: str = mea_loc
        self.mea_val: float = mea_val
        self.mea_dim: str = mea_dim
        self.mea_time: str = mea_time
        self.timestamp: float = timestamp
        if self.timestamp == 0:
            self.timestamp = time.time()
        self.mea_hash: str = self.generate_id_hash()

    def generate_id_hash(self):
        """Function adds a unique ID to the row"""
        return HaFu.single_sha256_byte2byte(bytes(
            "{}{}".format(self.mea_type, self.timestamp),
            "utf-8")).hex()[:16]

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

    def __repr__(self):
        return "{:<16}-{:>12}: {:>6}{:<5}".format(self.mea_hash,
                                                  self.mea_loc,
                                                  self.mea_val,
                                                  self.mea_dim,
                                                  self.timestamp)

# CLASS definitions ENDED                                                                   -   ENDED   -
