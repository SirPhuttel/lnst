"""
This module defines the Param class, it's type specific derivatives
(IntParam, StrParam) and the Parameters class which serves as a container for
Param instances. This can be used by a BaseRecipe class to specify
optional/mandatory parameters for the entire test, or by HostReq and DeviceReq
classes to define specific parameters needed for the matching algorithm.
"""

__author__ = """
olichtne@redhat.com (Ondrej Lichtner)
"""

import copy
import re
from ipaddress import AddressValueError, IPv4Network, IPv6Network, NetmaskValueError
from socket import AddressFamily
from typing import Optional, Union

from lnst.Common.DeviceRef import DeviceRef
from lnst.Common.IpAddress import BaseIpAddress, ipaddress
from lnst.Common.LnstError import LnstError

class ParamError(LnstError):
    pass

class Param(object):
    """Base Parameter class

    Can be used to define your own specific parameter type. Param derived
    classes serve as *type checkers* to enable earlier failure of the recipe.

    :param mandatory: if `True`, marks the parameter as mandatory
    :type mandatory: bool

    :param default: the default value for the parameter, is also type-checked,
        immediately at Param object creation
    """
    def __init__(self, mandatory=False, **kwargs):
        self.mandatory = mandatory
        if "default" in kwargs:
            self.default = self.type_check(kwargs["default"])

    def type_check(self, value):
        """The type check method

        Implementation depends on the specific Param derived class.

        :return: the type checked or converted value

        :raises: :any:`ParamError` if the type check or conversion is invalid
        """
        return value

class ConstParam(Param):
    def __init__(self, value):
        super().__init__(default=value)

    def type_check(self, value):
        if hasattr(self, "default") and value != self.default:
            raise ParamError(f"Different value for constant parameter was provided ({value} != {self.default})")
        return value

class IntParam(Param):
    def type_check(self, value):
        try:
            return int(value)
        except ValueError:
            raise ParamError("Value must be a valid integer")

class FloatParam(Param):
    def type_check(self, value):
        try:
            return float(value)
        except ValueError:
            raise ParamError("Value must be a valid float")

class StrParam(Param):
    def type_check(self, value):
        try:
            return str(value)
        except ValueError:
            raise ParamError("Value must be a string")

class BoolParam(Param):
    def type_check(self, value):
        if isinstance(value, bool):
            return value
        else:
            raise ParamError("Value must be a boolean")

class IpParam(Param):
    def __init__(
            self,
            family: Optional[AddressFamily] = None,
            multicast: bool = False,
            **kwargs,
    ):
        self.require_family = family
        self.require_multicast = multicast
        super().__init__(**kwargs)

    def type_check(self, value):
        try:
            value = ipaddress(value)
        except LnstError:
            raise ParamError("Value must be a BaseIpAddress object")
        if self.require_family and value.family != self.require_family:
            raise ParamError(f"Value must be of type {self.require_family.name}")
        if self.require_multicast and not value.is_multicast:
            raise ParamError("Value must be a multicast address")
        return value

class HostnameParam(Param):
    def type_check(self, value):
        if not isinstance(value, str) or len(value) > 255:
            raise ParamError("Value must be a valid hostname string")

        hostname_re = (r"^([A-Z0-9]|[A-Z0-9][A-Z0-9\-]{0,61}[A-Z0-9])"
                       r"(\.([A-Z0-9]|[A-Z0-9][A-Z0-9\-]{0,61}[A-Z0-9]))*$")
        if re.match(hostname_re, value, re.IGNORECASE):
            return value
        else:
            raise ParamError("Value must be a valid hostname string")

class HostnameOrIpParam(IpParam, HostnameParam):
    def type_check(self, value):
        try:
            return IpParam.type_check(self, value)
        except:
            try:
                return HostnameParam.type_check(self, value)
            except:
                raise ParamError("Value must be a valid hostname string, ipaddress string or a BaseIpAddress object.")

class DeviceParam(Param):
    def type_check(self, value):
        # runtime import this because the Device class arrives on the Agent
        # during recipe execution, not during Agent init
        from lnst.Devices.Device import Device
        if isinstance(value, Device) or isinstance(value, DeviceRef):
            return value
        else:
            raise ParamError("Value must be a Device or DeviceRef object."
                             " Not {}".format(type(value)))

class DeviceOrIpParam(Param):
    def type_check(self, value):
        # runtime import this because the Device class arrives on the Agent
        # during recipe execution, not during Agent init
        from lnst.Devices.Device import Device
        if (isinstance(value, Device) or isinstance(value, DeviceRef) or
            isinstance(value, BaseIpAddress)):
            return value
        else:
            raise ParamError("Value must be a Device, DeviceRef or BaseIpAddress object."
                             " Not {}".format(type(value)))

class DictParam(Param):
    def type_check(self, value):
        if not isinstance(value, dict):
            raise ParamError("Value must be a Dictionary. Not {}"
                             .format(type(value)))
        else:
            return value

class ListParam(Param):
    def __init__(self, type=None, **kwargs):
        self._type = type
        super(ListParam, self).__init__(**kwargs)

    def type_check(self, value):
        if not isinstance(value, list):
            raise ParamError("Value must be a List. Not {}".format(type(value)))

        if self._type is None:
            return value

        new_value: list[str] = []
        for item in value:
            try:
                new_value.append(self._type.type_check(item))
            except ParamError as e:
                raise ParamError(f"Value '{item}' failed type check:\n{e}")
        return new_value


class ChoiceParam(Param):
    """Choice Param
    This parameter is used for sitiuation where a param can have one of
    a specified set of valid values. For example:

    >>> flow_type = ChoiceParam(type=StrParam, choices=set('tcp_rr', 'udp_rr', 'tcp_crr'))

    The type check will fail if the specified value does not pass both the specified
    subtype `type_check` or is not one of the specified choices.
    """
    def __init__(self, type=None, choices=set(), **kwargs):
        self._type = type() if type is not None else None
        self._choices = choices
        super().__init__(**kwargs)

    def type_check(self, value):
        if self._type is not None:
            value = self._type.type_check(value)
        if value not in self._choices:
            raise ParamError(f"Value '{value}' not one of {self._choices}")
        return value


class NetworkParam(Param):
    """Network Param

    Parameters of this type are used to specify a IPv4 or IPv6 networks.
    (network address + prefix length).

    For example::
        vlan0_ipv4 = IPv4NetworkParam(default="192.168.10.0/24")
        vlan0_ipv6 = IPv6NetworkParam(default="fc00:0:0:1::/64")
    """
    def __init__(self, type: Union[IPv4Network, IPv6Network], **kwargs):
        self._type = type
        super(NetworkParam, self).__init__(**kwargs)

    def type_check(self, value: str):
        try:
            return self._type(value)
        except (AddressValueError, NetmaskValueError) as e:
            raise ParamError(f"Value {value} failed type check") from e


class IPv4NetworkParam(NetworkParam):
    def __init__(self, **kwargs):
        super().__init__(IPv4Network, **kwargs)


class IPv6NetworkParam(NetworkParam):
    def __init__(self, **kwargs):
        super().__init__(IPv6Network, **kwargs)


class Parameters(object):
    def __init__(self):
        self._attrs = {}

    def __getattr__(self, name):
        if name == "_attrs":
            return object.__getattribute__(self, name)

        try:
            return self._attrs[name]
        except KeyError:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, val):
        if name == "_attrs":
            super(Parameters, self).__setattr__(name, val)
        else:
            self._attrs[name] = val

    def __delattr__(self, name):
        del self._attrs[name]

    def __contains__(self, name):
        return name in self._attrs

    def __iter__(self):
        for attr, val in list(self._attrs.items()):
            yield (attr, val)

    def _to_dict(self):
        return copy.deepcopy(self._attrs)

    def _from_dict(self, d):
        for name, val in list(d.items()):
            setattr(self, name, copy.deepcopy(val))

    def __str__(self):
        result = ""
        for attr, val in list(self._attrs.items()):
            result += "%s = %s\n" % (attr, str(val))
        return result

    def get(self, name, default=None):
        """
        This method is used similar to `dict.get()`. It can be used to check if a param
        is in the Parameters object, and if not returns some other value.

        For example::
                if "perf_tool_cpu" in self.params
                    cpuin = self.params.perf_tool_cpu
                else:
                    cpuin = 1

        Becomes::
            cpuin = self.params.get('perf_tool_cpu', 1)

        :param name: The name of the parameter to query.
        :param default: The value to return if param `name` is not specified. Default None
        :return: The value of the parameter, if it was specified, otherwise the value of `default`.
        """
        if name in self:
            return self._attrs[name]
        else:
            return default
