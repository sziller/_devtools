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
from sqlalchemy.orm import sessionmaker

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger()
# Setting up logger                                         logger                      -   ENDED   -

Base = declarative_base()

# SESSION creation START                                                                    -   START   -


def createSession(db_fullname: str, tables: list or None = None, style: str = "SQLite", base=Base):
    """=== Function name: createSession ================================================================================
    Setting up a session to handle SQL DB operations.
    :param db_fullname: str - name of the DB (or the direct path to it - if PostgreSQL)
    :param tables: list - of __table__ parameters of each table-representing-class to be created on session init
    :param style: str - whether "SQLite" or "PostgreSQL" style DB is to be accessed
    :param base: Base object to be used in session creation
    :return: a session-object
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    cfn = inspect.currentframe().f_code.co_name  # current class name
    if style == "SQLite":
        engine = create_engine('sqlite:///%s' % db_fullname, echo=False, poolclass=NullPool)
    elif style == "PostGreSQL":
        engine = create_engine(db_fullname, echo=False, poolclass=NullPool)
    else:
        lg.critical("not found : '{}' is not a valid <style> value! - says {}()".format(style, cfn))
        raise Exception("no valid dialect defined")

    base.metadata.create_all(bind=engine, tables=tables)  # check if always necessary!!!
    Session = sessionmaker(bind=engine)
    return Session()

# SESSION creation ENDED                                                                    -   ENDED   -

# DB manipulating functions START                                                           -   START   -


def ADD_rows_to_table(primary_key: str,
                      data_list: list,
                      row_obj: Base,
                      session: sessionmaker.object_session):
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
    session.commit()
    return added_primary_keys


def DELETE_multiple_rows_by_filterkey(filterkey: str,
                                      filtervalue_list: list,
                                      row_obj: Base,
                                      session: sessionmaker.object_session):
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
                                            session: sessionmaker.object_session):
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
                                           session: sessionmaker.object_session):
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


def QUERY_entire_table(ordered_by: str,
                       row_obj: Base,
                       session: sessionmaker.object_session) -> list:
    """=== Function name: QUERY_entire_table ===========================================================================
    SQL action. You use the session entered. Function returns the entire DB table defined by <row_obj>.
    :param ordered_by: str -
    :param row_obj: Base - the class attached to the table you want to query
    :param session: session-obj - a pre-created session. It is NOT closed at the end of the function.
    :return: list of the rows of the table requested. Rows are represented as dictionaries.
    ============================================================================================== by Sziller ==="""
    # Current Function Name
    # cfn = inspect.currentframe().f_code.co_name  # current class name
    results = session.query(row_obj).order_by(ordered_by).all()
    result_list = [_.return_as_dict() for _ in results]
    session.commit()
    return result_list


def QUERY_rows_by_column_filtervalue_list_ordered(filterkey: str,
                                                  filtervalue_list: list,
                                                  ordered_by: str,
                                                  row_obj: Base,
                                                  session: sessionmaker.object_session) -> list:

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
    results = session.query(row_obj).filter(getattr(row_obj, filterkey).
                                            in_(tuple(filtervalue_list))).order_by(ordered_by)
    result_list = [_.return_as_dict() for _ in results]
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
