from clusto.schema import *
#from sqlalchemyhelpers import _AssociationMultiDict

    
class Thing(object):

    __metaclass__ = ClustoThing

    meta_attrs = {'clustotype': 'thing'}

    required_attrs = []
    
    # I can't get multivalued dict like behavior working quite right
    # and I'm not entirely sure that's the best interface anyway.
    #attrs = association_proxy('_attrs', 'value',
    #                          proxy_factory=_AssociationMultiDict)
    
    def __init__(self, name, *args, **kwargs):
        
        self.name = name


        #if thingtype:
        #    self.addAttr('clustotype', thingtype)
        if len(self.required_attrs) != (len(args) + len(kwargs)):
            raise TypeError(self.__class__.__name__ +
                            "() wrong number of arguments given.")
        

        reqattrs = list(self.required_attrs)

        for arg in kwargs:
            if arg in reqattrs:
                self.addAttr(arg, kwargs[arg])
                reqattrs.remove(arg)

        for arg in args:
            self.addAttr(reqattrs.pop(0), arg)


        
        for i in reversed(self.__class__.mro()):
            if hasattr(i, 'meta_attrs'):
                self.updateAttrs(i.meta_attrs, replaceAttrs=False)

        if hasattr(self, 'setup'):
            self.setup()
            


    def __new__(cls, *args, **kwargs):

        newthing = super(Thing, cls).__new__(cls, *args, **kwargs)
        #newthing._setProperClass()
        return newthing

    def _setProperClass(self):
        """
        Set the class for the proper object to the best suited driver
        """

        attrset = set(self.getAttrs())
        possible_classes = [ i for i in DRIVERLIST
                             if (attrset.issuperset(set(i._all_meta_attrs.items())))]


        # sort the possible_classes so that the most specific one is used
        # (the one with the most matching meta_attrs)
        # I'm not sure if this is the most correct behaviour
        possible_classes.sort(cmp=lambda x, y: cmp(len(x._all_meta_attrs.items()),
                                                   len(y._all_meta_attrs.items())),)
                              

        self.__class__ = possible_classes.pop(-1)

        
    def __str__(self):

        out = []
        for attr in self._attrs:
            out.append("%s.%s %s\n" % (self.name, attr.key, attr.value))

        for con in self.connections:
            out.append("%s.rel %s" % (self.name, con.name))

        return ''.join(out)

    def _get_connections(self):

        connlist = []
        
        ta = ThingAssociation.select(or_(ThingAssociation.c.thing_name1==self.name,
                                         ThingAssociation.c.thing_name2==self.name))

        for i in ta:
            itemname = (i.thing_name1 == self.name) \
                       and i.thing_name2 or i.thing_name1
            
            newthing = Thing.selectfirst_by(name=itemname)

            ## this is a crude brute force method of getting Things in the
            ## form of their respective driver objects
            ## I think I can just change __class__ for the object to make it
            ## work
            #newthing = driverlist[newthing.attrs['driver']].selectfirst_by(name=itemname)
            #newthing.__class__ = driverlist[newthing.attrs['driver']]
            #newthing._setProperClass()
            connlist.append(newthing)

        return connlist

    @classmethod
    def allMetaAttrs(self):

        allmeta = []
        for i in self.mro():
            if hasattr(i, 'meta_attrs'):
                allmeta.extend(i.meta_attrs.items())

        return allmeta

    connections = property(_get_connections)
    
    def disconnect(self, thing):

        conn = ThingAssociation.select(or_(ThingAssociation.c.thing_name1==self.name,
                                           ThingAssociation.c.thing_name2==self.name))

        for i in conn:
            i.delete()


    def connect(self, thing):

        ta = ThingAssociation(self, thing)
        
        

    def addAttr(self, key, value):
        """
        Add an attribute (key/value pair) to this Thing.

        Attribute keys can have multiple values.
        """
        self._attrs.append(Attribute(key, value))

    def addAttrs(self, attrlist):
        """
        Add a list or dict of attributes to this Thing.

        Takes in a list of the form [(key1, value1), (key2, value2), ...] or
        a dictionary.  If a dictionary in the key has a value which is a list
        then that is recorded as multiple attrubutes
        (i.e. (key, value1), (key, value2), (key, value3) ...
        """
        
        if isinstance(attrlist, dict):
            attrlist = attrlist.items()
            
        for attr in attrlist:

            if isinstance(attr[1], list):
                for value in attr[1]:
                    self.addAttr(attr[0], value)
            else:
                self.addAttr(attr[0], attr[1])


    def delAttr(self, key, value):
        """
        Delete the attribute matching the given key/value pair
        """
        attr = filter(lambda x: x.key == key and x.value == value, self._attrs)
        for i in attr:
            self._attrs.remove(i)

    def delAttrs(self, key):
        """
        Delete all attributes with the given key
        """
        attrlist = filter(lambda x: x.key == key, self._attrs)

        for i in attrlist:
            self._attrs.remove(i)
            
        

        
    def getAttrs(self, keys=None, asdict=False):
        """
        Returns a list of the key value pairs of the attributes associated
        with this Thing.

        When keys is specified it will only return those keys, otherwise it'll
        return all attributes.
        
        If asdict is True then it'll return a dictionary where the values are
        all lists.  
        """

        attrs = self._attrs
        
        if keys:
            attrlist = [(i.key, i.value)
                        for i in attrs if i.key in keys]
            
        else:
            attrlist = [(i.key, i.value) for i in attrs]


        if asdict:
            attrlist = AttributeDict(attrlist)
            
        return attrlist

    def getAttr(self, key, justone=True):
        """
        returns the first value of a given key.

        if justone is False then return all values for the given key.
        """
        
        attrlist = filter(lambda x: x.key == key, self._attrs)

        return justone and attrlist[0].value or [a.value for a in attrlist]

    def hasAttr(self, key):

        attrlist = filter(lambda x: x.key == key, self._attrs)

        return attrlist and True or False

    def setAttrs(self, key, valuelist):
        """
        Set the given key to the given valuelist.

        This will first clear all the attributes with the given key then
        add attributes with the key/value pairs where the value comes from
        the valuelist.
        """

        self.delAttrs(key)
        self.addAttrs(((key,v) for v in valuelist))

    def setAttr(self, keyval, newval):
        """
        Set a given key value pair with a new value.

        keyval is a (key, value) tuple
        """
        # this is kind of innefficient

        attr = filter(lambda x: x.key == keyval[0] and x.value == keyval[1],
                      self._attrs)

        if not attr:
            self.addAttr(keyval, newval)
        else:
            attr[0].value = newval
        
    def updateAttrs(self, attrdict, replaceAttrs=True):
        """
        Update attributes from a given dict.

        If replaceAttrs is True then Attributes that have keys from attrdict
        get removed and replaced with values from attrdict.

        If a value from attrdict is a list then the elements from that list
        get used to construct multiple key/value pairs where the key is the
        key for that value list and the value is an element of the value list.
        
        """

        if replaceAttrs:
            for newkey in attrdict:
                self.delAttrs(newkey)
            
        self.addAttrs(attrdict.items())
            
            
    def getConnectedMatching(self, matchdict):
        """
        Get the objects this Thing is directly connected to that match the
        given criteria.

        matchdict should be AttributeDict compatible
        """

        return [athing for athing in self.connections if athing.isMatch(matchdict)]

    def isMatch(self, matchdict):
        """
        Does this Thing match the given matchdict.

        """

        ## this has got to be a fairly slow way of doing this

        keyshare = [x.key for x in self._attrs]

        for key in matchdict:
            if key not in keyshare:
                return False
            
            matchedkeys = [x.value for x in self._attrs if x.key == key]
            matchedkeys.sort()
            
            values = matchdict[key]

            values.sort()

            if values != matchedkeys:
                return False

        return True

    def searchSelfAndPartsForAttrs(self, query):
        """
        search for information about myself and my Parts
        """

        pass
    
    def isPart(self):
        return isinstance(self, Part)

    
        

class Resource(Thing):
    meta_attrs = {'clustotype' : 'resource' }

    


class Part(Thing):

    meta_attrs = {'clustotype' : 'part' }

