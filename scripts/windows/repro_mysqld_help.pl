#!/usr/bin/env perl
# Runs "mysqld --verbose --help" in a loop the way mtr's
# collect_mysqld_features() does, and reports every run whose output
# differs from a complete reference run. Exits 1 if any run differed.
#
# Run from the build's mysql-test directory:
#   perl repro_mysqld_help.pl [mysqld path] [runs] [worker id] [pipe|file]
#
# "pipe" reads the output through backticks, like mtr; "file" redirects it
# to a file and reads the file after mysqld has exited.
use strict;
use warnings;
use POSIX qw(strftime);

my $mysqld = $ARGV[0] // '../sql/RelWithDebInfo/mysqld.exe';
my $runs   = $ARGV[1] // 1000;
my $worker = $ARGV[2] // 0;
my $mode   = $ARGV[3] // 'pipe';
die "mode must be pipe or file\n" unless $mode =~ /^(pipe|file)$/;

my $outdir = 'repro-out';
mkdir $outdir unless -d $outdir;

my $cmd = join(' ', $mysqld,
  '--no-defaults',
  '--datadir=.',
  '--basedir=..',
  '--lc-messages-dir=../sql/share',
  '--skip-grant-tables',
  '--log-warnings=0',
  '--log-slow-admin-statements=0',
  '--log-queries-not-using-indexes=0',
  '--log-slow-slave-statements=0',
  '--verbose',
  '--help');

$| = 1;

sub now { strftime('%Y-%m-%d %H:%M:%S', localtime) }

sub run_once {
  if ($mode eq 'file') {
    my $file = "$outdir/help-$worker.out";
    unlink $file;
    system("$cmd > \"$file\"");
    my ($status, $native) = ($?, ${^CHILD_ERROR_NATIVE});
    open my $fh, '<', $file or return ('', $status, $native);
    local $/;
    my $out = <$fh> // '';
    close $fh;
    return ($out, $status, $native);
  }
  my $out = `$cmd`;
  return ($out, $?, ${^CHILD_ERROR_NATIVE});
}

# The last thing mysqld --verbose --help prints
sub is_complete { $_[0] =~ /^To see what (variables|values) a running/m }

sub save {
  my ($file, $text) = @_;
  open my $fh, '>:raw', $file or die "$file: $!";
  print {$fh} $text;
  close $fh;
}

my $ref;
for my $try (1 .. 10) {
  my ($out, $status) = run_once();
  if ($status == 0 && is_complete($out)) {
    $ref = $out;
    last;
  }
  printf "%s worker %d: reference attempt %d incomplete (\$?=%d, %d bytes)\n",
    now(), $worker, $try, $status, length($out);
}
die "worker $worker: no complete reference output from: $cmd\n"
  unless defined $ref;

save("$outdir/reference-$worker.txt", $ref);
printf "%s worker %d (%s): reference is %d bytes, cmd: %s\n",
  now(), $worker, $mode, length($ref), $cmd;

my $bad = 0;
for my $i (1 .. $runs) {
  my ($out, $status, $native) = run_once();
  if ($out ne $ref) {
    $bad++;
    my $len = length($out);
    # offset of the first byte that differs from the reference
    (my $xor = $out ^ substr($ref, 0, $len)) =~ /^\0*/;
    my $diff = $+[0];
    my ($last_line) = $out =~ /([^\n]*)\n?\z/;
    my $file = "$outdir/bad-$worker-$i.txt";
    save($file, $out);
    printf "%s MISMATCH worker %d iteration %d: exit code %d (\$?=%d, native=%d), "
         . "%d of %d bytes, %s, lost %d bytes, length %% 4096 = %d, "
         . "last line '%s', saved %s\n",
      now(), $worker, $i, $status >> 8, $status, $native, $len, length($ref),
      $diff == $len ? 'prefix of reference' : "differs from byte $diff",
      length($ref) - $len, $len % 4096, $last_line, $file;
  }
  printf "%s worker %d: %d done, %d mismatches\n", now(), $worker, $i, $bad
    if $i % 100 == 0;
}
printf "%s worker %d (%s): finished %d runs, %d mismatches\n",
  now(), $worker, $mode, $runs, $bad;
exit($bad ? 1 : 0);
