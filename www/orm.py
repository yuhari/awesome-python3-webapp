#!/usr/bin/env python3
__author__ = 'yuhari'

import logging, aiomysql
import asyncio

### box mysql actions

def log(sql, args=()):
    logging.info('SQL: %s' % sql)
    
async def create_pool(loop, **kw):
    logging.info('create database connection pool ...')
    global __pool
    __pool = await aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        port = kw.get('port', 3306),
        user = kw.get('user', 'yuhari'),
        password = kw.get('password', 'calors'),
        db = kw['db'],
        charset = kw.get('charset', 'utf8'),
        autocommit = kw.get('autocommit', True),
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 1),
        loop = loop
    )

async def select(sql, args, size=None):
    log(sql, args)
    with await __pool as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

async def execute(sql, args, autocommit=True):
    log(sql)
    with await __pool as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected

### ORM classes

## define data type field
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    
    def __str__(self):
        return '<%s, %s: %s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(50)'):
        super().__init__(name, ddl, primary_key, default)

class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0, ddl='int(11)'):
        super().__init__(name, ddl, primary_key, default)

class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'double', primary_key, default)

class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class TextField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'text', False, default)

## define meta class that relate model attrs and fields
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return super().__new__(cls, name, bases, attrs)
        
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table %s)' % (name, tableName))
        mappings = dict()
        fields = []
        primaryKey = None
        for k,v in attrs.items():
            if isinstance(v, Field):
                logging.info(' found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        # mappings : save the relationship between attr and table row's word
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        # fields :attrs name except primary key
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, ', '.join('?' * (len(escaped_fields) + 1)))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

## define Model class that relate db tables and attrs
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute called '%s'" % key)
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def getValue(self, key):
        return getattr(self, key)
    
    def setValue(self, key, value):
        return setattr(self, key, value)
    
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s')
                setattr(self, key, value)
        return value
    
    @classmethod
    # find by primary key
    async def find(cls, pk): 
        logging.info('find object by primary key: %s' % pk)
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), (pk,), 1)
        if len(rs) == 0:
            return None
        #return a class that named 'cls' and params are rs[0]
        return cls(**rs[0])
    
    @classmethod
    #find by where clause
    async def findAll(cls, where=None, args=None, **kw):
        logging.info('find objects by where clause.')
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy :
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit :
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]
    
    @classmethod
    #find count(*) by where clause
    async def findNumber(cls, selectField, where=None, args=None, **kw):
        logging.info('find count by where clause.')
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        limit = kw.get('limit', None)
        if limit :
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']
    
    # model save()
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)
    
    # model update()
    async def update(self):
        args = list(map(self.getValue, self__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update record: affected rows: %s' % rows)
    
    # model delete() by pk
    async def delete(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove record: %s, affected rows: %s' % (self.__primary_key__, rows))