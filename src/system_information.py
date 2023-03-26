#
#
#

import psutil
import ipaddress
from socket import AddressFamily
from pyroute2 import IPRoute

from collections import defaultdict

from moulinette import m18n
from moulinette.utils import process
from moulinette.utils.log import getActionLogger

from yunohost.utils.error import YunohostError, YunohostValidationError

logger = getActionLogger("yunohost.system-information")


def system_information_network_interfaces():
    interfaces = psutil.net_if_addrs()
    interface_status = psutil.net_if_stats()

    interfaces_formated = defaultdict(dict)

    for interface in interfaces:
        if str(interface) == "lo":
            continue

        if interface in interface_status and interface_status[interface].isup:
            interfaces_formated[interface]["status"] = "UP"
        else:
            interfaces_formated[interface]["status"] = "DOWN"

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


def system_information_network_routes():

###
# Linux routing tables:
#    255     local      1
#    254     main       2
#    253     default    3
#    0       unspec     4
###

    with IPRoute() as ipr:
        interfaces = system_information_network_interfaces()
        ips_interface = {}
        for interface in interfaces:
            for family in ["ip4", "ip6"]:
                for address in interfaces[interface][family]:
                    ips_interface[address["address_short"]] = interface

        routes = []
        for route in ipr.get_routes():
            # Only get the routes from the main routing table
            if route.get_attr("RTA_TABLE") != 254:
                continue

            if (route.get_attr("RTA_DST") or route.get_attr("RTA_GATEWAY")):

                # We don't print the routes related to the loopback because it's not really interesting
                if route.get_attr("RTA_PREFSRC") and \
                        ("127.0.0.1" in [route.get_attr("RTA_PREFSRC"), route.get_attr("RTA_PREFDST")]):
                    continue

                # If no dest and no gateway this route is not interesting either
                if not route.get_attr("RTA_DST") and not route.get_attr("RTA_GATEWAY"):
                    continue

                # If no OIF it is blackhole or unreachable
                if route.get_attr("RTA_OIF"):
                    reachable = True

                    # Get OIF
                    if not route.get_attr("RTA_DST"):
                        if route["family"] == 2:
                            destination = "0.0.0.0/0"
                        else:
                            destination = "::/0"
                    else:
                        destination = f"{str(route.get_attr('RTA_DST'))}/{str(route.get('dst_len'))}"

                    if route.get_attr("RTA_PREFSRC"):
                        src = str(route.get_attr("RTA_PREFSRC"))
                    else:
                        full_route = ipr.route('get', dst=destination)
                        src = str(full_route[0]["attrs"][3][1])
                    interface = ips_interface[src]

                    # TODO Get metric
                else:
                    # Interface is not reachable because no OIF
                    # It can be "unreachable", "blackhole" or "prohibit"
                    reachable = False
                    interface = None
                    metric = None
                    src = None
                    destination = f"{str(route.get_attr('RTA_DST'))}/{str(route.get('dst_len'))}"

                routes.append({"family": "ip4" if route["family"] == 2 else "ip6",
                               "destination": destination,
                               "interface": interface,
                               "src": src,
                               "metric": metric,
                               "reachable": reachable})

    return {"routes": routes}

def system_information_network_gateway():
    return []
