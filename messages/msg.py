""" Defining the basic message object to communicate inside SmartHome system
by Sziller"""

from pydantic import BaseModel
from typing import Any

class MsgObject:
    """=== Class name: MsgObject ====================================================================================
    Two way communication Object between Server and Engine, Server and Subservers
    ============================================================================================== by Sziller ==="""
    def __init__(self,
                 payload: Any,
                 timestamp: float   = 0.0,
                 **kwargs):
        # every communication message Object must have a timestamp defined on init:
        # this is the unique ID of the object on code level
        self.payload: Any                   = payload
        self.timestamp: float               = timestamp

    def as_dict(self) -> dict:
        """=== Method name: as_dict ====================================================================================
        Returns actual state of instance as a dictionary.
        :return dict: parameter: args <- in current state
        ========================================================================================== by Sziller ==="""
        return {_: getattr(self, _) for _ in self.__dict__}

    @classmethod
    def init_by_dict(cls, **kwargs):
        """=== Classmethod name: generate_from_dict ====================================================================
        Lets you define an instance by dictionary
        ========================================================================================== by Sziller ==="""
        return cls(**kwargs)


class InternalMsg(MsgObject):
    """
    :param instant: bool -  if True:    we wait for the Engine to process the call, and return Engine response to API:
                                        Request-Response message management.
                            if False:   we return a default answer to API, in oorder not to block socket data flow.:
                                        Fire-and-Forget message management.
    """
    def __init__(self,
                 payload: Any,
                 timestamp: float   = 0.0,
                 synced: bool       = False,
                 email: str         = "",
                 signature: bytes   = b'',
                 command: str       = "",
                 **kwargs):
        super(InternalMsg, self).__init__(payload=payload, timestamp=timestamp, **kwargs)
        self.synced: bool               = synced
        self.email: str                 = email
        self.signature: bytes or None   = signature
        self.command: str = command


class ExternalResponseMsg(MsgObject):
    def __init__(self,
                 payload: Any,
                 timestamp: float   = 0.0,
                 message: str       = "",
                 **kwargs):
        super(ExternalResponseMsg, self).__init__(payload=payload, timestamp=timestamp, **kwargs)
        self.message: str       = message
        

class MsgModel(BaseModel):
    """=== Model name: MsgModel(BaseModel) ===============================  
    Model representing basic messaging inside Backend and towards Frontend  
    ==================================================== by Sziller ==="""
    timestamp: float = 0.0
    payload: Any     = None


class ExtRespMsg(MsgModel):
    """=== Model name: ExtRespMsg(MsgModel) ==============================  
    Extended Model representing messaging towards Frontend  
    ==================================================== by Sziller ==="""
    message: str = ""

    
