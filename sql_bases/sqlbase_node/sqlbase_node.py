"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, JSON, Float, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for local Base handling   START                                                   -   START   -
# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()


class Node(Base):
    """=== Classname: Node(Base) =======================================================================================
    Class represents a Node Database Entry who's data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "nodes"
    alias: str                      = Column("alias", String, primary_key=True)
    owner: str                      = Column("owner", String)
    ip: str                         = Column("ip", String)
    port: int                       = Column("port", Integer)
    features: dict                  = Column("features", JSON)
    desc: str                       = Column("desc", String)
    is_rpc: bool                    = Column("is_rpc", Integer)

    __table_args__ = (UniqueConstraint('alias', name='uq_alias_lower'),)  # Ensure alias is unique (case insensitive)
    
    def __init__(self,
                 alias: str,
                 owner: str,
                 ip: str,
                 port: int,
                 features: dict,
                 desc: str,
                 is_rpc: int):
        self.alias: str     = alias.lower()
        self.owner: str     = owner
        self.ip: str        = ip
        self.port: int      = port
        self.features: dict = features
        self.desc: str      = desc
        self.is_rpc: int    = is_rpc

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
