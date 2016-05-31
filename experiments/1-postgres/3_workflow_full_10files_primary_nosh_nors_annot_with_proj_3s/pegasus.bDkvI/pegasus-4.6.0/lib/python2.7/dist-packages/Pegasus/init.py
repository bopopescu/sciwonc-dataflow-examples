import sys
import os
import stat
from jinja2 import Environment, FileSystemLoader

def choice(question, options, default):
    "Ask the user to choose from a short list of named options"
    while True:
        sys.stdout.write("%s (%s) [%s]: " % (question, "/".join(options), default))
        answer = sys.stdin.readline().strip()
        if len(answer) == 0:
            return default
        for opt in options:
            if answer == opt:
                return answer

def yesno(question, default="y"):
    "Ask the user a yes/no question"
    while True:
        sys.stdout.write("%s (y/n) [%s]: " % (question, default))
        answer = sys.stdin.readline().strip().lower()
        if len(answer) == 0:
            answer = default
        if answer == 'y':
            return True
        elif answer == 'n':
            return False

def query(question, default=None):
    "Ask the user a question and return the response"
    while True:
        if default:
            sys.stdout.write("%s [%s]: " % (question, default))
        else:
            sys.stdout.write("%s: " % question)
        answer = sys.stdin.readline().strip()
        if answer == "":
            if default:
                return default
        else:
            return answer

def optionlist(question, options, default=0):
    "Ask the user to choose from a list of options"
    for i, option in enumerate(options):
        print "%d: %s" % (i+1, option[0])
    while True:
        sys.stdout.write("%s (1-%d) [%d]: " % (question, len(options), default+1))
        answer = sys.stdin.readline().strip()
        if len(answer) == 0:
            return options[default][1]
        try:
            optno = int(answer)
            if optno > 0 and optno <= len(options):
                return options[optno-1][1]
        except:
            pass

class Workflow(object):
    def __init__(self, workflowdir, sharedir):
        self.jinja = Environment(loader=FileSystemLoader(sharedir), trim_blocks=True)
        self.name = os.path.basename(workflowdir)
        self.workflowdir = workflowdir
        self.sharedir = sharedir
        self.properties = {}
        self.home = os.environ["HOME"]
        self.user = os.environ["USER"]

    def copy_template(self, template, dest, mode=0644):
        "Copy template to dest in workflowdir with mode"
        path = os.path.join(self.workflowdir, dest)
        t = self.jinja.get_template(template)
        t.stream(**self.__dict__).dump(path)
        os.chmod(path, mode)

    def mkdir(self, path):
        "Make relative directory in workflowdir"
        path = os.path.join(self.workflowdir, path)
        if not os.path.exists(path):
            os.makedirs(path)

    def configure(self):
        # The tutorial is a special case
        if yesno("Do you want to generate the tutorial workflow?", "n"):
            self.config = "tutorial"
            self.daxgen = "tutorial"
            self.sitename = "condorpool"
            return

        # Determine which DAX generator API to use
        self.daxgen = choice("What DAX generator API do you want to use?", ["python","perl","java"], "python")

        # Determine what kind of site catalog we need to generate
        self.config = optionlist("What does your computing infrastructure look like?", [
            ("Condor Pool", "condorpool"),
            ("Remote Cluster using Globus GRAM", "globus"),
            ("Remote Cluster using CREAMCE", "creamce"),
            ("Local PBS Cluster with Glite", "glite"),
            ("Remote PBS Cluster with BOSCO and SSH", "bosco")
        ])

        # Determine name of compute site
        self.sitename = query("What do you want to call your compute site?", "compute")

    def generate(self):
        os.makedirs(self.workflowdir)
        self.mkdir("input")
        self.mkdir("output")

        if self.config == "tutorial":
            self.copy_template("tutorial/tc.txt", "tc.txt")
            self.copy_template("tutorial/daxgen.py", "daxgen.py")

            # Executables used by the tutorial
            self.mkdir("bin")
            self.copy_template("tutorial/transformation.py", "bin/preprocess", mode=0755)
            self.copy_template("tutorial/transformation.py", "bin/findrange", mode=0755)
            self.copy_template("tutorial/transformation.py", "bin/analyze", mode=0755)

            # Tutorial input file
            self.copy_template("tutorial/f.a", "input/f.a")
        else:
            self.copy_template("tc.txt", "tc.txt")
            if self.daxgen == "python":
                self.copy_template("daxgen/daxgen.py", "daxgen.py")
            elif self.daxgen == "perl":
                self.copy_template("daxgen/daxgen.pl", "daxgen.pl")
            elif self.daxgen == "java":
                self.copy_template("daxgen/DAXGen.java", "DAXGen.java")
            else:
                assert False

        self.copy_template("sites.xml", "sites.xml")
        self.copy_template("plan_dax.sh", "plan_dax.sh", mode=0755)
        self.copy_template("generate_dax.sh", "generate_dax.sh", mode=0755)
        self.copy_template("README.md", "README.md")
        self.copy_template("rc.txt", "rc.txt")
        self.copy_template("pegasus.properties", "pegasus.properties")

def usage():
    print "Usage: %s WORKFLOW_DIR" % sys.argv[0]

def main(pegasus_share_dir):
    if len(sys.argv) != 2:
        usage()
        exit(1)

    if "-h" in sys.argv:
        usage()
        exit(1)

    workflowdir = sys.argv[1]
    if os.path.exists(workflowdir):
        print "ERROR: WORKFLOW_DIR '%s' already exists" % workflowdir
        exit(1)

    workflowdir = os.path.abspath(workflowdir)
    sharedir = os.path.join(pegasus_share_dir, "init")
    w = Workflow(workflowdir, sharedir)
    w.configure()
    w.generate()

