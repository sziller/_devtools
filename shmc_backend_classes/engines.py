"""===
by Sziller ==="""

from sql_access.sql_interface import createSession
from multiprocessing import Queue
from sqlalchemy.orm import Session
from sz_messages.msg import InternalMsg
import logging
import inspect
import os

# LOGGING                                                                                   logging - START -
lg = logging.getLogger()
# LOGGING                                                                                   logging - ENDED -


class EngineID:
    """=== Class name: EngineID ========================================================================================
    ClassID for Base Engine
    ============================================================================================== by Sziller ==="""   
    def __init__(self,
                 engine_id: str):
        self.engine_id: str                 = engine_id
            
        
class BaseEngine(EngineID):
    """=== Class name: BaseEngine ======================================================================================
    Class carrying basic Engine functionality
    ============================================================================================== by Sziller ==="""
    def __init__(self,
                 engine_id: str,
                 finite_looping: int        = 0):
        super().__init__(engine_id)
        self.finite_looping: int            = finite_looping
    

class AutonomousEngine(BaseEngine):
    """=== Class name: AutonomousEngine ================================================================================
    Class to define an Engine communicating only over DB
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    ccn = inspect.currentframe().f_code.co_name  # current class name
    
    def __init__(self,
                 engine_id: str,
                 finite_looping: int                            = 0,
                 session: Session or None                       = None,
                 session_name: str or None                      = None,
                 session_style: str or None                     = None):
        super().__init__(engine_id, finite_looping)
        self.session: Session or None                           = session
        self.session_name: str or None                          = session_name
        self.session_style: str or None                         = session_style
        self.manage_session()
        
    def manage_session(self):
        """=== Method name: manage_session =============================================================================
        Method  either  confirms the use of a pre-created session entered
                or      uses <session_name> and <session_style> to make a local session.
        Code doesn't block flow if session does not created at the end.
        :return:
        ========================================================================================== by Sziller ==="""
        if self.session is not None:
            lg.debug("database  : using entered session - says: {} at {}".format(
                self.ccn, os.path.basename(__file__)))
        else:
            lg.debug("database  : no session received, setting up local session - says: {} at {}".format(
                self.ccn, os.path.basename(__file__)))
            if self.session_name is None or self.session_style is None:
                lg.error(
                    "database  : couldn't find 'name' or 'style'. No useable session exists - says: {} at {}".format(
                        self.ccn, os.path.basename(__file__)))
            else:
                try:
                    self.session = createSession(db_fullname=self.session_name, tables=None, style=self.session_style)
                except:
                    lg.critical("database  : failed to create session - says: {} at {}".format(
                        self.ccn, os.path.basename(__file__)))
        if not isinstance(self.session, Session):
            lg.critical("database  : unrecognized session type - says: {} at {}".format(
                self.ccn, os.path.basename(__file__)))


class InteractiveEngine(AutonomousEngine):
    """=== Class name: InteractiveEngine ===============================================================================
    Class to define an Engine communicating bi-directionally over multiprocess.Queues
    ============================================================================================== by Sziller ==="""
    
    def __init__(self,
                 engine_id: str,
                 finite_looping: int                            = 0,
                 session: Session or None                       = None,
                 session_name: str or None                      = None,
                 session_style: str or None                     = None,
                 queue_hub_to_eng: Queue or None                = None,
                 queue_eng_to_hub: Queue or None                = None,
                 ):
        super().__init__(engine_id, finite_looping, session, session_name, session_style)
        self.queue_hub_to_eng: Queue or None        = queue_hub_to_eng
        self.queue_eng_to_hub: Queue or None        = queue_eng_to_hub
        self.actual_request: InternalMsg or None    = None
        self.took_n_queued_last_loop: int           = 0
        
    def pop_last_entry_from_queue_in(self):
        """=== Method name: pop_last_entry_from_queue_in ===============================================================
        Suggesting self.queue_hub_to_eng to include data, method takes last member.
        Last member is:
        - stored under self.actual_request
        - deleted from queue_in
        If self.queue_hub_to_eng is empty on call, nothig happens, method passes.
        ___________ (by Instance we refer to the Instance of THIS very Class) _____________________________________
        :var self.actual_request - dict      : the dict storing the actual <directcall> - updatable loop by loop.
                                                  This variable might be MODIFIED
        :var self.queue_hub_to_eng - queue  : queue to pass data TO Instance. (from whatever source e.g.: UI
                                                  This variable is READ (checked)
        :return nothing
        ========================================================================================== by Sziller ==="""
        cmn = inspect.currentframe().f_code.co_name  # current method name
        self.took_n_queued_last_loop = 0
        try:
            if not self.queue_hub_to_eng.empty():  # only if Queue is not empty... having at least 1 element.
                lg.info("QUEUE--in - <self.queue_hub_to_eng>: {} sees   {:>3} object.".format(cmn, self.queue_hub_to_eng.qsize()))
                lg.info("QUEUE--in - <self.queue_hub_to_eng>: {} POPPING...".format(cmn))
                self.actual_request = self.queue_hub_to_eng.get()  # <self.actual_request> takes first incoming obj
                lg.info("QUEUE--in - <self.queue_hub_to_eng>: {} popped {:>3} object.".format(cmn, 1))
                lg.info("QUEUE--in - <self.queue_hub_to_eng>: {} sees   {:>3} object.".format(cmn, self.queue_hub_to_eng.qsize()))
                self.took_n_queued_last_loop = 1
        except Exception as e:
            lg.critical("QUEUE--in - <self.queue_hub_to_eng>: {} encountered an error:\n{}".format(cmn, e))
            
