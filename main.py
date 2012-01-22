#!/usr/bin/env python3
import sys, getopt
import util
from tf import *

alloc = Alloc()
class Configuration(object):
  verbose  = True
  noChecks = False
  debug    = False
  tmpDir   = '/tmp/git-tf'
  number   = None
  dryRun   = False

  def readFromGit(self):
    def readValue(name):
      value = git('config tf.%s' % name, errorMsg = 'git tf is not configured. Config value "%s" not found.' % name)
      setattr(self, name, value)

    readValue('domain')
    readValue('username')

  def parseArgs(self, args):
    optlist, args = getopt.getopt(args, 'vCn:', 'verbose debug noChecks dry-run number='.split())
    shortToLong = {
      'v': 'verbose',
      'C': 'noChecks',
      'n': 'number'
    }

    for arg, value in optlist:
      if arg[1] != '-':
        long = shortToLong.get(arg[1:])
        if not long: fail('Unknown option ' + arg)
      else:
        long = arg[2:]

      long = toCamelCase(long)
      setattr(self, long, value == '' or value)

    if self.number is not None:
      self.number = int(self.number)

cfg = Configuration()

def usage():
  print('Usage is not written yet. Sorry.')

def init():
  root = git('rev-parse --show-toplevel')

  cfg.readFromGit()

  origDir = os.path.abspath('.')
  os.chdir(root)
  alloc.append(lambda : os.chdir(origDir))

  if git('status -s') != '':
    fail('Worktree is dirty')

  if not cfg.noChecks:
    print('Checking TFS status. There must be no pending changes...')
    workfold = tf('workfold .')
    if workfold.find(root) == -1:
      print('TF mapped folder does not match git root work folder!')
      print('Expected: %s' % root)
      print('Actual: %s' % workfold.splitlines()[3].split(': ')[1])
      fail()

    if tf('status') != 'There are no matching pending changes.':
      fail('TFS status is dirty!')

  origBranch = git('status -sb')[3:]
  if origBranch == 'HEAD (no branch)':
    fail('Not currently on any branch')
  git('checkout tfs')
  alloc.append(lambda: git('checkout ' + origBranch))

  os.environ['GIT_NOTES_REF'] = 'refs/notes/tf'

  if not os.path.exists(cfg.tmpDir):
    os.mkdir(cfg.tmpDir)
  alloc.append(lambda: os.rmdir(cfg.tmpDir))

allowedCommands = 'fetch pull push'.split()
def runCommand(command, cfg):
  if command in allowedCommands:
    module = __import__(command)
    if module:
      return getattr(module, command)(cfg)

  fail('Command %s not found' % command)

def main():
  args = sys.argv[1:]
  if not args:
    usage()
    return
  command = args.pop(0)
  if command.startswith('-'):
    usage()
    return

  cfg.parseArgs(args)
  if cfg.dryRun:
    print('DRY RUN. Nothing is going to be changed.\n')
  util.displayCommands = cfg.debug
  init()
  runCommand(command, cfg)

if __name__ == '__main__':
  exitCode = 0
  try:
    main()
  except GitTfException:
    exitCode = 1
  finally:
    alloc.free()
  quit(exitCode)