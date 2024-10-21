"""
Kudos to Tim and his YT authentication and authorization tutorials!
"""

import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from sql_access import sql_interface as sqli
from sql_bases.sqlbase_user.sqlbase_user import User as sqlUser

load_dotenv()

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
AUTH_ALGO = os.getenv("AUTH_ALGO")
AUTH_TOKEN_EXPIRE_MINS = os.getenv("AUTH_TOKEN_EXPIRE_MINS")

DB_FULLNAME_AUTH = os.getenv("DB_FULLNAME_AUTH")
DB_STYLE_AUTH = os.getenv("DB_STYLE_AUTH")

oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def actual_db_state() -> list:
    """=== Function name: actual_db_state ==============================================================================
    Function returns the actual state of the Auth database in real time
    ============================================================================================== by Sziller ==="""
    loc_session = sqli.createSession(db_fullname=DB_FULLNAME_AUTH, tables=None, style=DB_STYLE_AUTH)
    data = sqli.QUERY_entire_table(ordered_by="timestamp", row_obj=sqlUser, session=loc_session)
    loc_session.close()
    return data
    

class User(BaseModel):
    """=== Model name: User(BaseModel) ===================================  
    Model representing a user inside dev. scope  
    ============================================== by Sziller & Tim ==="""
    username: str
    email: str
    usr_ln: str             = ""
    usr_fn: str             = ""
    auth_code: int          = 0
    pubkey: str             = ""
    disabled: bool          = False


class UserInDB(User):
    """=== Model name: User(BaseModel) ===================================  
    Extended Model representing a user inside dev. scope  
    ============================================== by Sziller & Tim ==="""
    psswd_hsh: str


class Token(BaseModel):
    """=== Model name: Token =============================================  
    Model representing authentication Token  
    ==================================================== by Sziller ==="""
    access_token: str  # the actual Token
    token_type: str  # type of the Token
    
    
class TokenData(BaseModel):
    username: str or None   = None


def verify_psswd(plain_psswd: str, psswd_hsh: str) -> bool:
    """=== Function name: verify_psswd =================================================================================
    Quick routine to check if password matches it's alleged hash.
    :param plain_psswd: str - psswd to be verified
    :param psswd_hsh: str - hash to check against
    :return: boolean - True for match, False if doesn't
    ============================================================================================== by Sziller ==="""
    return pwd_context.verify(plain_psswd, psswd_hsh)


def get_user_data(db_lines: list[dict], username: str) -> UserInDB or False:
    """=== Function name: get_user_data ================================================================================
    Using a list of key:value pair represented DB data, function returns User data as a predefined class
    :param db_lines: list - of database lines
    :param username: str - actual username
    :return a class of User-data (if found) or False (if not found)
    ======================================================================================== by Sziller & Tim ==="""
    for usr_line in db_lines:
        if usr_line["username"] == username:
            return UserInDB(**usr_line)
    return False


def authenticate_user(db_lines, username: str, psswd: str) -> UserInDB or False:
    """=== Function name: authenticate_user ============================================================================
    Using a list of key:value pair represented DB data, function checks if username and password match
    :param db_lines: list - of database lines
    :param username: str - actual username
    :param psswd: str - assumed password
    :return a class of User-data (if verified) or False (if password couldn't be verified)
    ============================================================================================== by Sziller ==="""
    usr_data = get_user_data(db_lines=db_lines, username=username)
    if not usr_data:
        return False
    if not verify_psswd(psswd, usr_data.psswd_hsh):
        return False
    return usr_data


async def get_current_user(token: str = Depends(oauth_2_scheme)):
    """=== Function name: get_current_user =============================================================================
    Function - as dependency - checks Bearer token. Raises exceptions if Token doesn't fit.
    :param token: JWT token
    :return: the valid user represented by the Token
    ======================================================================================== by Sziller & Tim ==="""
    # creating default Error message:
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldnt validate",
                                         headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGO])
        username: str = payload.get("sub")
        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credential_exception

    user = get_user_data(db_lines=actual_db_state(), username=token_data.username)
    if user is None:
        raise credential_exception
    return user


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    """=== Function name: get_current_active_user ======================================================================
    Function - as dependency - checks if user is disabled, raises exception for disabled user.
    :param current_user: user to be checked
    :return: the same user
    ======================================================================================== by Sziller & Tim ==="""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

if __name__ == "__main__":
    pass
