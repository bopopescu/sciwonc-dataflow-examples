import sys
import re
import os
from optparse import OptionParser

from Pegasus.cluster import RecordParser

class JobFailed(Exception): pass

def rotate_file(outfile, errfile):
    """Rename .out and .err files to .out.XXX and .err.XXX where XXX
    is the next sequence number. Returns the new name, or fails with
    an error message and a non-zero exit code."""

    # This is just to prevent the file from being accidentally renamed 
    # again in testing.
    if re.search("\.out\.[0-9]{3}$", outfile):
        return outfile, errfile

    # Must end in .out
    if not outfile.endswith(".out"):
        raise JobFailed("%s does not look like a kickstart .out file" % outfile)

    # Find next file in sequence
    retry = None
    for i in range(0,1000):
        candidate = "%s.%03d" % (outfile,i)
        if not os.path.isfile(candidate):
            retry = i
            break

    # unlikely to occur
    if retry is None:
        raise JobFailed("%s has been renamed too many times!" % (outfile))

    basename = outfile[:-4]

    # rename .out to .out.000
    newout = "%s.out.%03d" % (basename,retry)
    os.rename(outfile,newout)

    # rename .err to .err.000 if it exists
    newerr = None
    if os.path.isfile(errfile):
        newerr = "%s.err.%03d" % (basename,retry)
        os.rename(errfile,newerr)

    return newout, newerr

def readfile(filename):
    # If the file does not exits, return empty string
    if filename is None or not os.path.isfile(filename):
        return ""

    f = open(filename, "r")
    try:
        return f.read()
    finally:
        f.close()

def find_cluster_summary(txt):
    "Find and return the cluster summary record if it exists"

    b = txt.find("[cluster-summary")
    if b < 0:
        # Older seqexec used this name
        b = txt.find("[seqexec-summary")
    if b >= 0:
        e = txt.find("]", b)
        if e < 0:
            raise JobFailed("Invalid cluster-summary record")

        return RecordParser(txt[b:e+1]).parse()

    # If we found a cluster-task, but no cluster-summary, then theres a problem
    b = txt.find("[cluster-task")
    if b >= 0:
        raise JobFailed("cluster-summary is missing")

    return None

def check_cluster_summary(record):
    "Make sure that the cluster-summary record is OK"

    if "stat" in record:
        stat = record["stat"]
        if stat != "ok":
            raise JobFailed("cluster-summary stat=%s" % stat)

    # If any of the tasks failed, then job failed
    if "failed" in record:
        failed = int(record["failed"])
        if failed > 0:
            raise JobFailed("cluster-summary failed=%d" % failed)

    # If no tasks were submitted, then it succeeded
    if "submitted" in record:
        submitted = int(record["submitted"])
        if submitted == 0:
            return 0

    # If there were no tasks, then the job was successful
    if "tasks" in record:
        tasks = int(record["tasks"])
        if tasks == 0:
            return 0

    # If the number of successes was zero, then the job failed
    if "succeeded" in record:
        succeeded = int(record["succeeded"])
        if succeeded == 0:
            raise JobFailed("cluster-summary succeeded=%d" % succeeded)

    return 0

def check_kickstart_records(txt):

    # Check the exitcodes of all kickstart records
    regex = re.compile(r'raw="(-?[0-9]+)"')
    succeeded = 0
    e = 0
    while True:
        b = txt.find("<status", e)
        if b < 0: break
        e = txt.find("</status>", b)
        if e < 0: raise JobFailed("mismatched <status>")
        e = e + len("</status>")
        m = regex.search(txt[b:e])
        if m: raw = int(m.group(1))
        else: raise JobFailed("<status> was missing valid 'raw' attribute")
        if raw != 0:
            raise JobFailed("task exited with raw status %d" % raw)
        succeeded = succeeded + 1

    # Fail if there were no invocation records and no cluster-summary
    if succeeded == 0:
        raise JobFailed("No successful kickstart records")

    return 0

def unquote_message(message):
    def genchars():
        for c in message:
            yield c

    chars = genchars()
    output = []
    for c in chars:
        if c == '+':
            output.append(' ')
        elif c == '\\':
            try:
                c = chars.next()
            except StopIteration:
                output.append(c)
                break
            if c == '+':
                output.append('+')
            else:
                output.append('\\')
                output.append(c)
        else:
            output.append(c)

    return "".join(output)

def unquote_messages(messages):
    return [unquote_message(m) for m in messages]

def has_any_failure_messages(stdio, messages):
    """Return true if any of the messages appear in the files"""
    if len(messages) == 0:
        return False

    messages = unquote_messages(messages)

    for txt in stdio:
        for m in messages:
            if m in txt:
                return True

    return False

def has_all_success_messages(stdio, messages):
    """Return true if any of the messages don't appear in the files"""
    if len(messages) == 0:
        return True

    messages = unquote_messages(messages)

    found = set()
    for txt in stdio:
        for m in messages:
            if m in txt:
                found.add(m)

    for m in messages:
        if m not in found:
            return False

    return True

def get_errfile(outfile):
    """Get the stderr file name given the stdout file name"""
    i = outfile.rfind(".out")
    left = outfile[0:i]
    right = ""
    if i + 5 < len(outfile):
        right = outfile[i+4:]
    errfile = left + ".err" + right
    return errfile

def exitcode(outfile, status=None, rename=True,
             failure_messages=[], success_messages=[]):

    if not os.path.isfile(outfile):
        raise JobFailed("%s does not exist" % outfile)

    errfile = get_errfile(outfile)

    # If we are renaming, then rename
    if rename:
        outfile, errfile = rotate_file(outfile, errfile)

    # First, check exitcode supplied by DAGMan, if any
    if status is not None:
        if status != 0:
            raise JobFailed("dagman reported non-zero exitcode: %d" % status)

    # Next, read the output and error files
    stdout = readfile(outfile)
    stderr = readfile(errfile)

    # Next, check the size of the output file
    if len(stdout) == 0:
        raise JobFailed("Empty stdout")

    # Next, if we have failure messages, then fail if we find one in the
    # output of the job
    if has_any_failure_messages([stdout, stderr], failure_messages):
        raise JobFailed("Failure message found in output")

    # Next, if we have success messages, then fail if we don't find all
    # in the output of the job
    if not has_all_success_messages([stdout, stderr], success_messages):
        raise JobFailed("Success message missing from output")

    # Next, check exitcodes of all tasks
    cs = find_cluster_summary(stdout)
    if cs is not None:
        check_cluster_summary(cs)
    else:
        # PM-927 Only check kickstart records if -r is not supplied
        if status is None:
            check_kickstart_records(stdout)

def main(args):
    usage = "Usage: %prog [options] job.out"
    parser = OptionParser(usage)

    parser.add_option("-r", "--return", action="store", type="int",
        dest="status", metavar="R",
        help="Return code reported by DAGMan. This can be specified in a "
             "DAG using the $RETURN variable.")
    parser.add_option("-n", "--no-rename", action="store_false",
        dest="rename", default=True,
        help="Don't rename kickstart.out and .err to .out.XXX and .err.XXX. "
             "Useful for testing.")
    parser.add_option("-f", "--failure-message", action="append",
        dest="failure_messages", default=[],
        help="Failure message to find in job stdout/stderr. If this "
             "message exists in the stdout/stderr of the job, then the "
             "job will be considered a failure no matter what other "
             "output exists. If multiple failure messages are provided, "
             "then none of them can exist in the output or the job is "
             "considered a failure.")
    parser.add_option("-s", "--success-message", action="append",
        dest="success_messages", default=[],
        help="Success message to find in job stdout/stderr. If this "
             "message does not exist in the stdout/stderr of the job, "
             "then the job will be considered a failure no matter what "
             "other output exists. If multiple success messages are "
             "provided, then they must all exist in the output or "
             "the job is considered a failure.")

    (options, args) = parser.parse_args(args)

    if len(args) != 1:
        parser.error("Please specify job.out")

    outfile = args[0]

    try:
        exitcode(outfile, status=options.status, rename=options.rename,
                 failure_messages=options.failure_messages,
                 success_messages=options.success_messages)
        sys.exit(0)
    except JobFailed, jf:
        print jf
        sys.exit(1)

