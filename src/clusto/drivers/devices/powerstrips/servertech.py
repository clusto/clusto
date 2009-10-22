"""
Server Technology Power Strips

"""


from basicpowerstrip import BasicPowerStrip
from clusto.drivers.devices.common import IPMixin
from clusto.drivers import IPManager
from clusto.exceptions import DriverException

import netsnmp
import re


class PowerTowerXM(BasicPowerStrip, IPMixin):
    """
    Provides support for Power Tower XL/XM

    Power Port designations start with 1 at the upper left (.aa1) down to 32
    at the bottom right (.bb8).
    """

    _driver_name = "powertowerxm"

    _properties = {'withslave':0}


    _portmeta = { 'pwr-nema-L5': { 'numports':2 },
                  'pwr-nema-5' : { 'numports':16, },
                  'nic-eth' : { 'numports':1, },
                  'console-serial' : { 'numports':1, },
                  }



    _portmap = {'aa1':1,'aa2':2,'aa3':3,'aa4':4,'aa5':5,'aa6':6,'aa7':7,'aa8':8,
                'ab1':9,'ab2':10,'ab3':11,'ab4':12,'ab5':13,'ab6':14,'ab7':15,
                'ab8':16,'ba1':17,'ba2':18,'ba3':19,'ba4':20,'ba5':21,'ba6':22,
                'ba7':23,'ba8':24,'bb1':25,'bb2':26,'bb3':27,'bb4':28,'bb5':29,
                'bb6':30,'bb7':31,'bb8':32}

    _outlet_states = ['idleOff', 'idleOn', 'wakeOff', 'wakeOn', 'off', 'on', 'lockedOff', 'reboot', 'shutdown', 'pendOn', 'pendOff', 'minimumOff', 'minimumOn', 'eventOff', 'eventOn', 'eventReboot', 'eventShutdown']

    def _ensure_portnum(self, porttype, portnum):
        """map powertower port names to clusto port numbers"""

        if not self._portmeta.has_key(porttype):
            msg = "No port %s:%s exists on %s." % (porttype, str(num), self.name)
                    
            raise ConnectionException(msg)

        if isinstance(portnum, int):
            num = portnum
        else:
            if portnum.startswith('.'):
                portnum = portnum[1:] 
            
            if self._portmap.has_key(portnum):
                num = self._portmap[portnum]
            else:
                msg = "No port %s:%s exists on %s." % (porttype, str(num), 
                                                       self.name)
                    
                raise ConnectionException(msg)
 
        numports = self._portmeta[porttype]
        if self.withslave:
            if porttype in ['mains', 'pwr']:
                numports *= 2

        if num < 0 or num >= numports:
            msg = "No port %s:%s exists on %s." % (porttype, str(num), 
                                                   self.name)
                    
            raise ConnectionException(msg)



        return num

    def _create_snmp_session(self):
        ip = IPManager.get_ips(self)
        if not ip:
            raise DriverException('Power switch %s has no IP address' % self.name)
        ip = ip[0]

        community = self.attr_values(key='snmp', subkey='community', merge_container_attrs=True)
        if not community:
            raise DriverException('Power switch %s has no key=snmp,subkey=community attribute' % self.name)
        community = community[0]

        return netsnmp.Session(Version=2, DestHost=ip, Community=community)

    def _get_port_oid_index(self, outlet, session=None):
        if not session:
            session = self._create_snmp_session()
        vars = netsnmp.VarList(netsnmp.Varbind('.1.3.6.1.4.1.1718.3.2.3.1.2'))
        for i, portname in enumerate(session.walk(vars)):
            if portname.lower() == outlet.lower().lstrip('.'):
                return '.'.join(vars[i].tag.rsplit('.', 3)[1:])

    def get_outlet_state(self, outlet, session=None):
        if not session:
            session = self._create_snmp_session()
        index = self._get_port_oid_index(outlet, session=session)
        oid = '.1.3.6.1.4.1.1718.3.2.3.1.10.%s' % index
        state = session.get(netsnmp.VarList(netsnmp.Varbind(oid)))
        state = state[0]
        if state == None:
            raise DriverException('Outlet %s does not exist' % outlet)
        return self._outlet_states[int(state)]

    def set_outlet_state(self, outlet, state, session=None):
        if not session:
            session = self._create_snmp_session()
        index = self._get_port_oid_index(outlet, session=session)
        oid = '.1.3.6.1.4.1.1718.3.2.3.1.11.%s' % index
        vars = netsnmp.VarList(netsnmp.Varbind(oid, '', state, 'INTEGER'))
        if session.set(vars) != 1:
            raise DriverException('Failed to set SNMP state %i for OID %s' % (state, oid))
            
    def reboot(self, porttype, portnum):
        if porttype != 'pwr-nema-5':
            raise DriverException('Cannot reboot ports of type: %s' % str(porttype))

        portnum = portnum.lstrip('.').lower()

        session = self._create_snmp_session()
        state = self.get_outlet_state(portnum, session=session)

        nextstate = None
        if state == 'off':
            nextstate = 1
        if state in ('idleOn', 'on'):
            nextstate = 3

        if not nextstate:
            raise DriverException('Outlet in unexpected state: %s' % state)

        self.set_outlet_state(portnum, nextstate, session=session)
