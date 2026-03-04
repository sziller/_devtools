"""
SQLAlchemy powered DB handling test, and production code.
you should be able to swap DB handling while using this SQLi from SQLite to PostgreSQL.
by Sziller
"""

import logging
import inspect
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """=== Event hook: set_sqlite_pragma ===============================================================================

    Ensures that SQLite foreign key constraints are enforced for every new
    database connection created by SQLAlchemy.

    Background
    ----------
    SQLite does NOT enforce foreign key constraints by default.
    Even if tables define ForeignKey(...) relationships, they remain
    non-operational unless explicitly enabled per connection via:

        PRAGMA foreign_keys = ON;

    This event listener attaches to the SQLAlchemy Engine "connect"
    event and activates foreign key enforcement automatically for
    every SQLite connection.

    Scope
    -----
    - Applies only to SQLite connections.
    - Has no effect on PostgreSQL or other database backends.
    - Executes once per newly established DBAPI connection.

    Architectural Importance
    -------------------------
    Required for referential integrity between tables such as:
        - users.uuid
        - liquidity_buckets.uuid (ForeignKey)

    Without this hook, orphan rows could be created silently,
    compromising financial consistency and data integrity.

    Fail-Safe Behavior
    ------------------
    The pragma is applied conditionally only when the DBAPI
    connection is an instance of sqlite3.Connection.

    ============================================================================================== by Sziller ==="""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


Base = declarative_base()

# SESSION creation START                                                                    -   START   -


# ---------------------------------------------------------------------------------------------------------
# ENGINE CACHE
# ---------------------------------------------------------------------------------------------------------

_engine_registry: dict[tuple[str, str], Engine] = {}


def _get_engine(db_fullname: str, style: str) -> Engine:
    """=== Internal function: _get_engine ============================================================================
    Returns a cached SQLAlchemy Engine instance for the given
    (db_fullname, style) combination.

    Purpose
    -------
    Ensures that:
        - Only one Engine is created per database configuration.
        - Connection pools are reused properly.
        - Expensive Engine creation does not occur repeatedly.
        - Behavior remains identical to previous implementation.

    Parameters
    ----------
    db_fullname : str
        Database file name (SQLite) or connection string (PostgreSQL).

    style : str
        Database dialect indicator.
        Supported values:
            - "SQLite"
            - "PostGreSQL"

    Returns
    -------
    Engine
        A SQLAlchemy Engine instance bound to the requested database.

    Architectural Notes
    --------------------
    - Engines are heavyweight and intended to live for the lifetime
      of the application.
    - Sessions are lightweight and may be created frequently.
    - This registry guarantees one Engine per database.

    Fail-Safe Behavior
    ------------------
    Raises Exception if unsupported style is provided.

    ============================================================================================== by Sziller ==="""
    style_normalized = style.strip().lower()
    key = (db_fullname, style_normalized)

    if key in _engine_registry:
        return _engine_registry[key]

    if style_normalized == "sqlite":
        engine = create_engine(
            f"sqlite:///{db_fullname}",
            echo=False,
            poolclass=NullPool,
            future=True
        )

    elif style_normalized in {"postgresql", "postgres"}:
        engine = create_engine(
            db_fullname,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            future=True
        )

    else:
        lg.critical("Invalid DB style: '%s' - sql-module refactored!!!", style)
        raise ValueError(f"Unsupported DB style: {style} - sql-module refactored!!!")

    _engine_registry[key] = engine
    return engine


# ---------------------------------------------------------------------------------------------------------
# SESSION CREATION
# ---------------------------------------------------------------------------------------------------------

def createSession(
        db_fullname: str,
        tables: list | None = None,
        style: str = "SQLite",
        base=Base
) -> Session:
    """=== Function name: createSession ================================================================================
    Creates and returns a SQLAlchemy Session object bound to the
    requested database configuration.

    This function preserves full backward compatibility with the
    previous implementation while internally improving engine
    lifecycle management.

    Parameters
    ----------
    db_fullname : str
        Name of the database (SQLite file) or full connection string
        (PostgreSQL).

    tables : list | None
        Optional list of ORM table objects (.__table__) that should
        be ensured to exist at session initialization.

    style : str
        Database dialect identifier:
            - "SQLite"
            - "PostGreSQL"

    base : declarative_base
        SQLAlchemy declarative base containing metadata definitions.

    Returns
    -------
    Session
        A SQLAlchemy Session instance ready for DB operations.

    Behavioral Guarantees
    ---------------------
    - Engine creation is cached and reused per database.
    - Session creation remains lightweight.
    - Table creation behavior is preserved.
    - No external API changes.
    - Fully safe drop-in replacement.

    Architectural Separation
    -------------------------
    - Engine lifecycle managed by _get_engine().
    - Session lifecycle managed here.
    - Foreign key enforcement handled globally via Engine connect event.

    ============================================================================================== by Sziller ==="""
    engine = _get_engine(db_fullname=db_fullname, style=style)

    # Ensure tables exist (if provided)
    if tables:
        base.metadata.create_all(bind=engine, tables=tables)

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

# SESSION creation ENDED                                                                    -   ENDED   -

# DB manipulating functions START                                                           -   START   -


def ADD_rows_to_table(primary_key: str,
                      data_list: list,
                      row_obj: Base,
                      session: Session):
    """=== Function name: ADD_rows_to_table ============================================================================
    SQL action. You use the session entered. Function simply fills in data represented in <data_list> into DB defined
    by <session_in>. Function will try to enter data into the Table defined by <row_obj>.
    ATTENTION: function does NOT close the session at the end! - you can continue using it.
    :param primary_key: str - the primary key of the row, defined by row_obj
    :param data_list: list[dict] row information in list of dictionaries format
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: list of primary keys - actually added
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    added_primary_keys = []
    for data in data_list:
        # there are cases:
        # - a. when primary key exists before instance being added to DB
        # - b. primary key is generated from other incoming data on instantiation
        if primary_key in data:  # a.: works only if primary key is set and included in row to be created!
            if not session.query(row_obj).filter(getattr(row_obj, primary_key) == data[primary_key]).count():
                newrow = row_obj.construct(d_in=data)
                session.add(newrow)
                added_primary_keys.append(data[primary_key])
        else:
            # this is the general case. <data> doesn't need to include primary key:
            # we check if primary key having been generated on instantiation exists.
            newrow = row_obj.construct(d_in=data)
            if not session.query(row_obj).filter(getattr(row_obj, primary_key) == getattr(newrow, primary_key)).count():
                session.add(newrow)
                added_primary_keys.append(getattr(newrow, primary_key))
            else:
                pass
    session.commit()
    return added_primary_keys


def DELETE_multiple_rows_by_filterkey(filterkey: str,
                                      filtervalue_list: list,
                                      row_obj: Base,
                                      session: Session):
    """=== DELETE_multiple_rows_by_filterkey ===========================================================================
    SQL action. You use the session entered. Function deletes rows, whoes <filterkey> colum's value is included in
    <filtervalue_list>. Function will try to delete data from the Table defined by <row_obj>.
    ATTENTION: function does NOT close the session at the end! - you can continue using it.
    :param filterkey: str - the key whoes values must be included in <filtervalue_list> in order for the parent row
                            to get deleted
    :param filtervalue_list: list - of values, one of which the filterkey must take in order for its parent row to be
                                    subject of this function
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: nothing
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    for filtervalue in filtervalue_list:
        session.query(row_obj).filter(getattr(row_obj, filterkey) == filtervalue).delete(synchronize_session=False)
    session.commit()


def MODIFY_multiple_rows_by_column_to_value(filterkey: str,
                                            filtervalue_list: list,
                                            target_key: str,
                                            target_value,
                                            row_obj: Base,
                                            session: Session):
    """=== Function name: MODIFY_multiple_rows_by_column_to_value ======================================================
    SQL action. You use the session entered. Function alters DB of all rows, whoes <filterkey>'s current value is
    represented in <filtervalue_list>.
    In these rows, the values of <target_keys> will become <target_value> after function is finished.
    USE THIS TO CHANGE ALL fo the filtered row's target_key's values to ONE specific value: the <target_value>.
    ATTENTION: function does NOT close the session at the end! - you can continue using it.
    :param filterkey: str - the key whoes values must be included in <filtervalue_list> in order for the parent row
                            to get altered
    :param filtervalue_list: list - of values, one of which the filterkey must take in order for its parent row to be
                                    subject of this function
    :param target_key: the name of the column that is subject to the change.
    :param target_value: the value, the actual row's <target_key> will take, once functon finishes
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: nothing
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    for filtervalue in filtervalue_list:
        session.query(row_obj).filter(getattr(row_obj, filterkey) == filtervalue).update({target_key: target_value})
    session.commit()


def MODIFY_multiple_rows_by_column_by_dict(filterkey: str,
                                           mod_dict: dict,
                                           row_obj: Base,
                                           session: Session):
    """=== Function name: MODIFY_multiple_rows_by_column_by_dict =======================================================
    SQL action. You use the session entered. Function alters DB of dedicated rows.
    Each rows <filterkey> column will be checked. If current value of a <filterey> is included in <mod_dict> as a key,
    then and only then <mod_dict>'s value (which is always a dictionary) will be applied to said row.
    Example:    name       age         points
                joe         12          20
                johny       13          32
                jenny       12          14
                henry       11          10
                jack        10          20
    
    filterkey: age
    mod_dict: {12: {'points': '0'}, 11: {'points': 'x'} }
    
    result:     name       age         points
                joe         12          0               <-- as age = 12, points is set to 0
                johny       13          32
                jenny       12          0               <-- as age = 12, points is set to 0
                henry       11          x               <-- as age = 11, points is set to x
                jack        10          20
        
    ATTENTION: function does NOT close the session at the end! - you can continue using it.
    :param filterkey: str - the key whoes values must be included in <mod_dict> as a key in order for the parent row
                            to get altered
    :param mod_dict: dict - of targetkeys : targetvalues. targetvalues are the new values
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: nothing
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    for filtervalue, sub_dict in mod_dict.items():
        session.query(row_obj).filter(getattr(row_obj, filterkey) == filtervalue).update(sub_dict)
    session.commit()


def QUERY_entire_table(session: Session,
                       row_obj: Base,
                       ordered_by: (str, None) = None
                       ) -> list:
    """=== Function name: QUERY_entire_table ===========================================================================
    SQL action. You use the session entered. Function returns the entire DB table defined by <row_obj>.
    :param ordered_by: str -
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: list of the rows of the table requested. Rows are represented as dictionaries.
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    table = row_obj.__table__ if hasattr(row_obj, '__table__') else row_obj
    query = session.query(row_obj)
    if ordered_by:
        query = query.order_by(ordered_by)
    results = query.all()
    # Convert each result row into a dictionary using table's columns
    result_list = [{column.name: getattr(row, column.name) for column in table.columns} for row in results]
    return result_list


def QUERY_rows_by_column_filtervalue_list_ordered(filterkey: str,
                                                  filtervalue_list: list,
                                                  ordered_by: str,
                                                  row_obj: Base,
                                                  session: Session) -> list:
    """=== Function name: QUERY_rows_by_column_filtervalue_list_ordered ================================================
    SQL action. You use the session entered. Function returns specific rows of the DB table defined by <row_obj>.
    Raws are selected if their value of <filterkey> is included in <filtervalue_list>.
    :param filterkey: str - the key (column) whoes values must be included in <filtervalue_list> in order
                            for the parent row to be included in the query
    :param filtervalue_list: list - of values, one of which the filterkey must take in order for its parent row to be
                                    subject of this function
    :param ordered_by: str -
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: list of the rows of the table requested. Rows are represented as dictionaries.
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    query = session.query(row_obj).filter(getattr(row_obj, filterkey).in_(tuple(filtervalue_list)))
    if ordered_by:
        query = query.order_by(getattr(row_obj, ordered_by))
    results = query.all()
    # Convert the result rows into dictionaries
    result_list = [{column.name: getattr(row, column.name) for column in row_obj.__table__.columns} for row in results]
    session.commit()
    return result_list


# DB manipulating functions ENDED                                                           -   ENDED   -


# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy import MetaData

# def drop_table(table_name, engine):
#     """
#     :param table_name:
#     :param engine:
#     :return:
#     """
#     Base = declarative_base()
#     metadata = MetaData()
#     metadata.reflect(bind=engine)
#     table = metadata.tables[table_name]
#     if table is not None:
#         Base.metadata.drop_all(engine, [table], checkfirst=True)


if __name__ == "__main__":
    pass
