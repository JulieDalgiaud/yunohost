#
#
#

import psutil
import ipaddress
from socket import AddressFamily

from collections import defaultdict

from moulinette import m18n
from moulinette.utils import process
from moulinette.utils.log import getActionLogger

from yunohost.utils.error import YunohostError, YunohostValidationError

logger = getActionLogger("yunohost.system-information")


def system_information_network_interfaces():
    interfaces = psutil.net_if_addrs()

    interfaces_formated = defaultdict(dict)

    for interface in interfaces:
        if str(interface) == "lo":
            continue

        for familly in ["ip4", "ip6"]:
            interfaces_formated[interface][familly] = []

            for instance in interfaces[interface]:
                tmp_info = {}
                if familly == "ip4" and instance.family != AddressFamily.AF_INET:
                    continue
                elif familly == "ip6" and instance.family != AddressFamily.AF_INET6:
                    continue

                address = instance.address.split("%")[0]
                netmask = instance.netmask

                if familly == "ip4":
                    network = str(ipaddress.IPv4Network(f"{address}/{netmask}", strict=False))
                    cidr = network.split("/")[-1]
                else:
                    bitCount = [0, 0x8000, 0xc000, 0xe000, 0xf000, 0xf800, 0xfc00, 0xfe00, 0xff00, 0xff80, 0xffc0, 0xffe0, 0xfff0, 0xfff8, 0xfffc, 0xfffe, 0xffff]
                    count = 0
                    for w in netmask.split(':'):
                        if not w or int(w, 16) == 0:
                            break
                        count += bitCount.index(int(w, 16))

                    cidr = str(count)
                    network = str(ipaddress.IPv6Network(f"{address}/{cidr}", strict=False))
                    tmp_info["netmask_expanded"] = netmask

                tmp_info["address"] = f"{address}/{cidr}"
                tmp_info["address_short"] = address
                tmp_info["netmask"] = netmask if familly == "ip4" else cidr
                tmp_info["network"] = network

                interfaces_formated[interface][familly].append(tmp_info)

    return interfaces_formated
