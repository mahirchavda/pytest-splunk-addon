import csv
import re
import string
import uuid

from datetime import datetime
from faker import Faker
from random import uniform, randint, choice
from time import strftime, mktime
from .time_parser import time_parse
import os

from . import SampleEvent


class Rule:
    user_header = ["name", "email", "domain_user", "distinquised_name"]
    src_header = ["host", "domain", "ipv4", "ipv6", "fqdn"]

    def __init__(self, token, eventgen_params=None):
        self.token = token["token"]
        self.replacement = token["replacement"]
        self.replacement_type = token["replacementType"]
        self.field = token.get("field", self.token.strip("#"))
        self.eventgen_params = eventgen_params
        self.fake = Faker()

    @classmethod
    def parse_rule(cls, token, eventgen_params):
        rule_book = {
            "integer": IntRule,
            "list": ListRule,
            "ipv4": Ipv4Rule,
            "float": FloatRule,
            "ipv6": Ipv6Rule,
            "mac": MacRule,
            "file": FileRule,
            "url": UrlRule,
            "user": UserRule,
            "email": EmailRule,
            "host": HostRule,
            "fqdn": FqdnRule,
            "hex": HexRule,
            "src_port": SrcPortRule,
            "dest_port": DestPortRule,
            "src": SrcRule,
            "dest": DestRule,
            "dvc": DvcRule,
        }

        replacement_type = token["replacementType"]
        replacement = token["replacement"]
        if replacement_type == "static":
            return StaticRule(token)
        elif replacement_type == "timestamp":
            return TimeRule(token, eventgen_params)
        elif replacement_type == "random" or replacement_type == "all":
            for each_rule in rule_book:
                if replacement.startswith(each_rule):
                    return rule_book[each_rule](token)
        elif replacement_type == "file":
            return FileRule(token)

        print("No Rule Found.!")
        # TODO: Test the behavior if no rule found
        raise Exception("No Rule Found.!")

    def apply(self, events):
        new_events = []
        for each_event in events:
            token_count = each_event.get_token_count(self.token)
            token_values = list(self.replace(each_event, token_count))
            if self.replacement_type == "all" and token_count > 0:
                # NOTE: If replacement_type is all and same token is more than
                #       one time in event then replace all tokens with same
                #       value in that event
                for each_token_value in token_values:
                    new_event = SampleEvent.copy(each_event)
                    new_event.replace_token(self.token, each_token_value)
                    new_event.register_field_value(
                        self.field, each_token_value
                    )
                    new_events.append(new_event)
            else:
                each_event.replace_token(self.token, token_values)
                each_event.register_field_value(self.field, token_values)
                new_events.append(each_event)
        return new_events

    def get_lookup_value(self, sample, filename, key, headers, value_list):
        f = open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        )
        reader = csv.reader(f)
        next(reader)

        index_list = [
            i
            for i, item in enumerate(headers)
            if item in value_list and item != "domain"
        ]
        csv_row = choice(list(reader))

        if (
            hasattr(sample, "replacement_map")
            and key in sample.replacement_map
        ):
            sample.replacement_map[key].append(csv_row)
        else:
            sample.__setattr__("replacement_map", {key: [csv_row]})

        return index_list, csv_row

    def get_rule_replacement_values(self, sample, value_list, rule):
        host_ip_list = sample.get_host_ipv4()
        host_ipv4 = "".join(
            ["10.1.", str(host_ip_list[0]), ".", str(host_ip_list[1])]
        )
        host_ipv6 = "{}:{}".format(
            "fdee:1fe4:2b8c:3264", sample.get_host_ipv6()
        )
        index_list, csv_row = self.get_lookup_value(
            sample,
            "lookups\\host_domain.csv",
            rule,
            self.src_header,
            value_list,
        )
        csv_row.append(host_ipv4)
        csv_row.append(host_ipv6)
        csv_row.append("{}.{}".format(csv_row[0], csv_row[1]))
        return index_list, csv_row


class IntRule(Rule):
    def replace(self, sample, token_count):
        lower_limit, upper_limit = re.match(
            r"[Ii]nteger\[(\d+):(\d+)\]", self.replacement
        ).groups()
        if self.replacement_type == "random":
            for _ in range(token_count):
                yield randint(int(lower_limit), int(upper_limit))
        else:
            for each_int in range(int(lower_limit), int(upper_limit)):
                yield each_int


class FloatRule(Rule):
    def replace(self, sample, token_count):
        lower_limit, upper_limit = re.match(
            r"[Ff]loat\[([\d\.]+):([\d\.]+)\]", self.replacement
        ).groups()
        precision = re.search("\[\d+\.?(\d*):", self.replacement).group(1)
        if not precision:
            precision = str(1)
        for _ in range(token_count):
            yield round(
                uniform(float(lower_limit), float(upper_limit)),
                len(precision),
            )


class ListRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(
            r"[lL]ist(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)

        if self.replacement_type == "random":
            for _ in range(token_count):
                yield str(choice(value_list))
        else:
            for each_value in value_list:
                yield str(each_value)


class StaticRule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            yield self.replacement


class FileRule(Rule):
    def replace(self, sample, token_count):
        sample_file_path = re.match(
            r"[fF]ile\[(.*?)\]", self.replacement
        ).group(1)
        if self.replacement_type == "random":
            try:
                f = open(sample_file_path)
                txt = f.read()
                f.close()
                lines = [each for each in txt.split("\n") if each]
                for _ in range(token_count):
                    yield choice(lines)
            except IOError:
                print("File not found : {}".format(sample_file_path))
        else:
            try:
                f = open(sample_file_path)
                txt = f.read()
                f.close()

                for each_value in txt.split("\n"):
                    yield each_value
            except IOError:
                print("File not found : {}".format(sample_file_path))


class TimeRule(Rule):
    def replace(self, sample, token_count):
        """
        input -> sample_raw - sample event to be updated as per replacement
                              for token.
              -> earliest - splunktime formated time.
              -> latest - splunktime formated time.
              -> timezone - time zone according to which time is to be
                            generated

        output -> returns random time according to the parameters specified in
                  the input.
        """
        earliest = self.eventgen_params.get("earliest")
        latest = self.eventgen_params.get("latest")
        timezone = self.eventgen_params.get("timezone")
        random_time = datetime.now()
        time_parser = time_parse()

        if earliest != "now" and earliest is not None:
            sign, num, unit = re.match(
                r"([+-])(\d{1,})(.*)", earliest
            ).groups()
            earliest = time_parser.convert_to_time(sign, num, unit)
        else:
            earliest = datetime.now()

        if latest != "now" and latest is not None:
            sign, num, unit = re.match(r"([+-])(\d{1,})(.*)", latest).groups()
            latest = time_parser.convert_to_time(sign, num, unit)
        else:
            latest = datetime.now()

        earliest_in_epoch = mktime(earliest.timetuple())
        latest_in_epoch = mktime(latest.timetuple())

        if earliest_in_epoch > latest_in_epoch:
            print("Latest time is earlier than earliest time.")
            yield self.token

        random_time = datetime.fromtimestamp(
            randint(earliest_in_epoch, latest_in_epoch)
        )
        if timezone != "'local'" and timezone is not None:
            sign, hrs, mins = re.match(
                r"([+-])(\d\d)(\d\d)", timezone
            ).groups()
            random_time = time_parser.get_timezone_time(
                random_time, sign, hrs, mins
            )

        if r"%s" in self.replacement:
            yield str(
                self.replacement.replace(
                    r"%s", str(int(random_time.strftime("%Y%m%d%H%M%S")))
                )
            )

        elif r"%e" in self.replacement:
            yield strftime(self.replacement.replace(r"%e", r"%d"))
        else:
            yield random_time.strftime(self.replacement)


class Ipv4Rule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            yield self.fake.ipv4()


class Ipv6Rule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            yield self.fake.ipv6()


class MacRule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            yield self.fake.mac_address()


class GuidRule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            yield str(uuid.uuid4())


class UserRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(
            r"[uU]ser(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)

        for i in range(token_count):
            if (
                hasattr(sample, "replacement_map")
                and "email" in sample.replacement_map
                and i < len(sample.replacement_map["email"])
            ):
                index_list = [
                    i
                    for i, item in enumerate(self.user_header)
                    if item in value_list
                ]
                csv_rows = sample.replacement_map["email"]
                yield csv_rows[i][choice(index_list)]
            else:
                index_list, csv_row = self.get_lookup_value(
                    sample,
                    "lookups\\user_email.csv",
                    "user",
                    self.user_header,
                    value_list,
                )
                yield csv_row[choice(index_list)]


class EmailRule(Rule):
    def replace(self, sample, token_count):

        for i in range(token_count):
            if (
                hasattr(sample, "replacement_map")
                and "user" in sample.replacement_map
                and i < len(sample.replacement_map["user"])
            ):
                index_list = [
                    i
                    for i, item in enumerate(self.user_header)
                    if item in ["email"]
                ]
                csv_rows = sample.replacement_map["user"]
                yield csv_rows[i][choice(index_list)]
            else:
                index_list, csv_row = self.get_lookup_value(
                    sample,
                    "lookups\\user_email.csv",
                    "email",
                    self.user_header,
                    ["email"],
                )
                yield csv_row[choice(index_list)]


class UrlRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(r"[uU]rl(\[.*?\])", self.replacement).group(
            1
        )
        value_list = eval(value_list_str)

        for _ in range(token_count):
            if bool(
                set(["ip_host", "fqdn_host", "full"]).intersection(value_list)
            ):
                url = ""
                domain_name = []
                if bool(set(["full", "protocol"]).intersection(value_list)):
                    url = url + choice(["http://", "https://"])
                if bool(set(["full", "ip_host"]).intersection(value_list)):
                    domain_name.append(self.fake.ipv4())
                if bool(set(["full", "fqdn_host"]).intersection(value_list)):
                    domain_name.append(self.fake.hostname())
                url = url + choice(domain_name)
            else:
                url = self.fake.url()

            if bool(set(["full", "path"]).intersection(value_list)):
                url = (
                    url
                    + "/"
                    + choice(
                        [
                            self.fake.uri_path(),
                            self.fake.uri_page() + self.fake.uri_extension(),
                        ]
                    )
                )

            if bool(set(["full", "query"]).intersection(value_list)):
                url = url + self.generate_url_query_params()
            yield str(url)

    """
    This method is generate the random query params for url
    Returns:
        Return the query param string
    """

    def generate_url_query_params(self):
        url_params = "?"
        for _ in range(randint(1, 4)):
            field = "".join(
                choice(string.ascii_lowercase) for _ in range(randint(2, 5))
            )
            value = "".join(
                choice(string.ascii_lowercase + string.digits)
                for _ in range(randint(2, 5))
            )
            url_params = url_params + field + "=" + value + "&"
        return url_params[:-1]


class DestRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(
            r"[dD]est(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)
        for _ in range(token_count):
            ipv4_addr = (
                "10.100." + str(randint(0, 255)) + "." + str(randint(1, 255))
            )
            ipv6_addr = "{}:{}".format(
                "fdee:1fe4:2b8c:3262", self.fake.ipv6()[20:]
            )
            index_list, csv_row = self.get_lookup_value(
                sample,
                "lookups\\host_domain.csv",
                "dest",
                self.src_header,
                value_list,
            )
            csv_row.append(ipv4_addr)
            csv_row.append(ipv6_addr)
            csv_row.append("{}.{}".format(csv_row[0], csv_row[1]))
            yield csv_row[choice(index_list)]


class SrcPortRule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            yield randint(4000, 5000)


class DvcRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(r"[dD]vc(\[.*?\])", self.replacement).group(
            1
        )
        value_list = eval(value_list_str)
        for _ in range(token_count):
            ipv4_addr = (
                "172.16." + str(randint(0, 255)) + "." + str(randint(1, 255))
            )
            ipv6_addr = "{}:{}".format(
                "fdee:1fe4:2b8c:3263", self.fake.ipv6()[20:]
            )
            index_list, csv_row = self.get_lookup_value(
                sample,
                "lookups\\host_domain.csv",
                "dvc",
                self.src_header,
                value_list,
            )
            csv_row.append(ipv4_addr)
            csv_row.append(ipv6_addr)
            csv_row.append("{}.{}".format(csv_row[0], csv_row[1]))
            yield csv_row[choice(index_list)]


class SrcRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(r"[sS]rc(\[.*?\])", self.replacement).group(
            1
        )
        value_list = eval(value_list_str)
        for _ in range(token_count):
            ipv4_addr = (
                "10.1." + str(randint(0, 255)) + "." + str(randint(1, 255))
            )
            ipv6_addr = "{}:{}".format(
                "fdee:1fe4:2b8c:3261", self.fake.ipv6()[20:]
            )
            index_list, csv_row = self.get_lookup_value(
                sample,
                "lookups\\host_domain.csv",
                "src",
                self.src_header,
                value_list,
            )
            csv_row.append(ipv4_addr)
            csv_row.append(ipv6_addr)
            csv_row.append("{}.{}".format(csv_row[0], csv_row[1]))
            yield csv_row[choice(index_list)]


class DestPortRule(Rule):
    def replace(self, sample, token_count):
        DEST_PORT = [80, 443, 25, 22, 21]
        for _ in range(token_count):
            yield choice(DEST_PORT)


class HostRule(Rule):
    def replace(self, sample, token_count):
        value_list_str = re.match(
            r"[hH]ost(\[.*?\])", self.replacement
        ).group(1)
        value_list = eval(value_list_str)
        for _ in range(token_count):
            index_list, csv_row = self.get_rule_replacement_values(
                sample, value_list, rule="host"
            )
            if sample.metadata.get("input_type") in [
                "modinput",
                "windows_input",
            ]:
                host_value = sample.metadata.get("host")
            elif sample.metadata.get("input_type") in [
                "file_monitor",
                "syslog",
                "scripted_input",
                "syslog_tcp",
                "syslog_udp",
                "other",
            ]:
                host_value = sample.get_host()
            csv_row[0] = host_value
            yield csv_row[choice(index_list)]


class FqdnRule(Rule):
    def replace(self, sample, token_count):
        for _ in range(token_count):
            index_list, csv_row = self.get_lookup_value(
                sample,
                "lookups\\host_domain.csv",
                "fqdn",
                self.user_header,
                ["fqdn"],
            )
            yield "{}.{}".format(csv_row[0], csv_row[1])


class HexRule(Rule):
    def replace(self, sample, token_count):
        hex_range = re.match(r"[Hh]ex\((.*?)\)", self.replacement).group(1)
        hex_digits = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
        ]
        hex_array = []
        for _ in range(token_count):
            for i in range(int(hex_range)):
                hex_array.append(hex_digits[randint(0, 15)])
            hex_value = "".join(hex_array)
            yield hex_value