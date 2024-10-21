"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for local Base handling   START                                                   -   START   -
# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()


class Utxo(Base):
    """=== Classname: Utxo(Base) =======================================================================================
    Class represents a Utxo Database Entry who's data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "utxoset"
    utxo_id: str = Column("utxo_id", String, primary_key=True)
    n: int = Column("n", Integer)
    txid: str = Column("txid", String)
    value: int = Column("value", Integer)
    addresses: list = Column("addresses", JSON)
    scriptPubKey_hex: str = Column("scriptPubKey_hex", String)
    scriptPubKey_asm: str = Column("scriptPubKey_asm", String)
    reqSigs: int = Column("reqSigs", Integer)
    scriptType: str = Column("scriptType", String)

    def __init__(self,
                 txid: str,
                 n: int,
                 value: int,
                 addresses: list,
                 scriptPubKey_hex: str,
                 scriptPubKey_asm: str,
                 reqSigs: int,
                 scriptType: str,
                 **kwargs):
        self.txid: str = txid
        self.n: int = n
        self.value: int = value
        self.addresses: list = addresses
        self.scriptPubKey_hex: str = scriptPubKey_hex
        self.scriptPubKey_asm: str = scriptPubKey_asm
        self.reqSigs: int = reqSigs
        self.scriptType: str = scriptType

        self.generate_utxo_id()

    def generate_utxo_id(self):
        """Function adds a unique ID to the row"""
        data = models.UtxoId(self.txid, self.n)
        self.utxo_id = "{}".format(data)

    def return_as_dict(self):
        """=== Method name: return_as_dict =============================================================================
        Returns instance as a dictionary
        @return : dict - parameter: argument pairs in a dict
        ========================================================================================== by Sziller ==="""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in, **kwargs):
        """=== Classmethod: construct ==================================================================================
        Input necessary class parameters to instantiate object of the class!
        @param d_in: dict - format data to instantiate new object
        @return: an instance of the class
        ========================================================================================== by Sziller ==="""
        return cls(**d_in)
