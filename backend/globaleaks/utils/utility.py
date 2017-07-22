# -*- coding: UTF-8
#   utility
#   *******
#
# GlobaLeaks Utility Functions
from __future__ import print_function

import cgi
import codecs
import ctypes
import inspect
import logging
import os
import re
import sys
import traceback
import uuid

from datetime import datetime, timedelta
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python import log as twlog
from twisted.python import util
from twisted.python.failure import Failure

from globaleaks import LANGUAGES_SUPPORTED_CODES


def uuid4():
    """
    This function returns a uuid4.

    The function is not intended to be used for security reasons.
    """
    return unicode(uuid.uuid4())


def sum_dicts(*dicts):
    ret = {}

    for d in dicts:
        for k, v in d.items():
            ret[k] = v

    return dict(ret)


def every_language(default_text):
    ret = {}

    for code in LANGUAGES_SUPPORTED_CODES:
        ret.update({code : default_text})

    return ret


def randint(start, end=None):
    if end is None:
        end = start
        start = 0
    w = end - start + 1
    return start + int(''.join("%x" % ord(x) for x in os.urandom(w)), 16) % w


def randbits(bits):
    return os.urandom(int(bits/8))


def choice(population):
    return population[randint(len(population) - 1)]


def shuffle(x):
    for i in reversed(xrange(1, len(x))):
        j = randint(0, i)
        x[i], x[j] = x[j], x[i]
    return x


def deferred_sleep(timeout):
    d = Deferred()

    def callbackDeferred():
        d.callback(True)

    reactor.callLater(timeout, callbackDeferred)

    return d


def msdos_encode(s):
    """
    This functions returns a new string with all occurences of newlines
    preprended with a carriage return.
    """
    gex = r'(\r\n)|(\n)'
    repl = '\r\n'
    return re.sub(gex, repl, s)


def log_encode_html(s):
    """
    This function encodes the following characters
    using HTML encoding: < > & ' " \ /
    """
    s = cgi.escape(s, True)
    s = s.replace("'", "&#39;")
    s = s.replace("/", "&#47;")
    s = s.replace("\\", "&#92;")

    return s


def log_remove_escapes(s):
    """
    This function removes escape sequence from log strings
    """
    if isinstance(s, unicode):
        return codecs.encode(s, 'unicode_escape')
    else:
        try:
            unicodelogmsg = str(s).decode('utf-8')
        except UnicodeDecodeError:
            return codecs.encode(s, 'string_escape')
        except Exception as e:
            return "Failure in log_remove_escapes %r" % e
        else:
            return codecs.encode(unicodelogmsg, 'unicode_escape')


class GLLogObserver(twlog.FileLogObserver):
    """
    Tracks and logs exceptions generated within the application
    """
    def emit(self, eventDict):
        """
        Handles formatting system log messages along with incrementing the objs
        error counters. The eventDict is generated by the arguments passed to each
        log level call. See the unittests for an example.
        """
        if 'failure' in eventDict:
            vf = eventDict['failure']
            e_t, e_v, e_tb = vf.type, vf.value, vf.getTracebackObject()
            sys.excepthook(e_t, e_v, e_tb)

        text = twlog.textFromEventDict(eventDict)
        if text is None:
            return

        timeStr = self.formatTime(eventDict['time'])
        fmtDict = {'system': eventDict['system'], 'text': text.replace("\n", "\n\t")}

        msgStr = twlog._safeFormat("[%(system)s] %(text)s\n", fmtDict)

        util.untilConcludes(self.write, timeStr + " " + log_encode_html(msgStr))
        util.untilConcludes(self.flush)


class Logger(object):
    """
    Customized LogPublisher
    """
    loglevel = logging.ERROR

    def setloglevel(self, loglevel):
        self.loglevel = loglevel

    def _print_logline(self, prefix, msg, *args):
        if not isinstance(msg, str) and not isinstance(msg, unicode):
            msg = str(msg)

        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')

        if len(args) > 0:
            msg = (msg % args)

        msg = log_remove_escapes(msg)

        print('[' + prefix + '] ' + msg)

    def debug(self, msg, *args):
        if self.loglevel and self.loglevel <= logging.DEBUG:
            self._print_logline('D', msg, *args)

    def info(self, msg, *args):
        if self.loglevel and self.loglevel <= logging.INFO:
            self._print_logline('I', msg, *args)

    def err(self, msg, *args):
        if self.loglevel:
            self._print_logline('E', msg, *args)

    def exception(self, error):
        """
        Error can either be an error message to print to stdout and to the logfile
        or it can be a twisted.python.failure.Failure instance.
        """
        if isinstance(error, Failure):
            error.printTraceback()
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)


log = Logger()


## time facilities ##


def datetime_null():
    """
    @return: a utc datetime object representing a null date
    """
    return datetime(1970, 1, 1, 0, 0)


def datetime_now():
    """
    @return: a utc datetime object for the current time
    """
    return datetime.utcnow()


def datetime_never():
    """
    @return: a utc datetime object representing the 1st January 3000
    """
    return datetime(3000, 1, 1, 0, 0)


def get_expiration(days):
    """
    @return: a utc datetime object representing an expiration time calculated as the current date + N days
    """
    date = datetime.utcnow()
    return datetime(year=date.year, month=date.month, day=date.day, hour=00, minute=00, second=00) + timedelta(days=days+1)


def is_expired(check_date, seconds=0, minutes=0, hours=0, day=0):
    """
    @param check_date: a datetime or a timestap
    @param seconds, minutes, hours, day
        the time to live of the element
    @return:
        if now > check_date + (seconds+minutes+hours)
        True is returned, else False
    """
    # TODO: this check may hide a bug a should be removed.
    #       (see commit message for details)
    if not check_date:
        return False

    total_hours = (day * 24) + hours
    check = check_date + timedelta(seconds=seconds, minutes=minutes, hours=total_hours)

    return datetime_now() > check


def datetime_to_ISO8601(date):
    """
    conver a datetime into ISO8601 date
    """
    # TODO: this check may hide a bug a should be removed.
    #       (see commit message for details)
    if date is None:
        date = datetime_null()

    return date.isoformat() + "Z" # Z means that the date is in UTC


def ISO8601_to_datetime(isodate):
    """
    convert an ISO8601 date into a datetime
    """
    isodate = isodate[:19] # we srip the eventual Z at the end

    try:
        ret = datetime.strptime(isodate, "%Y-%m-%dT%H:%M:%S")
    except ValueError :
        ret = datetime.strptime(isodate, "%Y-%m-%dT%H:%M:%S.%f")
        ret.replace(microsecond=0)
    return ret


def datetime_to_pretty_str(date):
    """
    print a datetime in pretty formatted str format
    """
    # TODO: this check may hide a bug a should be removed.
    #       (see commit message for details)
    if date is None:
        date = datetime_null()

    return date.strftime("%A %d %B %Y %H:%M (UTC)")


def ISO8601_to_day_str(isodate, tz=0):
    """
    print a ISO8601 in DD/MM/YYYY formatted str
    """
    # TODO: this check may hide a bug a should be removed.
    #       (see commit message for details)
    if isodate is None:
        isodate = datetime_null().isoformat()

    date = datetime(year=int(isodate[0:4]),
                    month=int(isodate[5:7]),
                    day=int(isodate[8:10]),
                    hour=int(isodate[11:13]),
                    minute=int(isodate[14:16]),
                    second=int(isodate[17:19]))

    if tz != 0:
        tz_i, tz_d = divmod(tz, 1)
        tz_d, _  = divmod(tz_d * 100, 1)
        date += timedelta(hours=tz_i, minutes=tz_d)

    return date.strftime("%d/%m/%Y")


def ISO8601_to_pretty_str(isodate, tz=0):
    """
    convert a ISO8601 in pretty formatted str format
    """
    if isodate is None:
        isodate = datetime_null().isoformat()

    date = datetime(year=int(isodate[0:4]),
                    month=int(isodate[5:7]),
                    day=int(isodate[8:10]),
                    hour=int(isodate[11:13]),
                    minute=int(isodate[14:16]),
                    second=int(isodate[17:19]) )

    if tz != 0:
        tz_i, tz_d = divmod(tz, 1)
        tz_d, _  = divmod(tz_d * 100, 1)
        date += timedelta(hours=tz_i, minutes=tz_d)
        return date.strftime("%A %d %B %Y %H:%M")

    return datetime_to_pretty_str(date)


def timedelta_to_milliseconds(t):
    return (t.microseconds + (t.seconds + t.days * 24 * 3600) * 10**6) / 10**3.0


def asn1_datestr_to_datetime(s):
    """
    Returns a datetime for the passed asn1 formatted string or None if the date.
    cannot be converted.
    """
    s = s[:14]
    try:
        return datetime.strptime(s, "%Y%m%d%H%M%S")
    except:
        return None


def format_cert_expr_date(s):
    """
    Takes a asn1 formatted date string and tries to create an expiration date
    out of it. If that does not work, the returned expiration date is never.
    """

    dt = asn1_datestr_to_datetime(s)
    if dt is None:
        return datetime_never()
    return dt


def iso_year_start(iso_year):
    """Returns the gregorian calendar date of the first day of the given ISO year"""
    fourth_jan = datetime.strptime('{0}-01-04'.format(iso_year), '%Y-%m-%d')
    delta = timedelta(fourth_jan.isoweekday() - 1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    """Returns gregorian calendar date for the given ISO year, week and day"""
    year_start = iso_year_start(iso_year)
    return year_start + timedelta(days=iso_day - 1, weeks=iso_week - 1)


def bytes_to_pretty_str(b):
    if b is None:
        b = 0

    if isinstance(b, str):
        b = int(b)

    if b >= 1000000000:
        return "%dGB" % int(b / 1000000000)

    if b >= 1000000:
        return "%dMB" % int(b / 1000000)

    return "%dKB" % int(b / 1000)


def caller_name(skip=2):
    """
    Get a name of a caller in the format module.class.method

    skip` specifies how many levels of stack to skip while getting caller
    name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

    An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
        # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append( codename ) # function or a method

    return ".".join(name)


def disable_swap():
    """
    use mlockall() system call to prevent the procss to swap
    """
    libc = ctypes.CDLL("libc.so.6", use_errno=True)

    MCL_CURRENT = 1
    MCL_FUTURE = 2

    log.debug("Using mlockall() system call to disable process swap")
    if libc.mlockall(MCL_CURRENT | MCL_FUTURE):
        log.err("mlockall failure: %s" % os.strerror(ctypes.get_errno()))
