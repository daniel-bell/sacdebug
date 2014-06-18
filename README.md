SACdebug
========

SACdebug is a collection of Python scripts with the aim to allow the debugging of [SAC](http://www.sac-home.org/) programs inside GDB.

## Installation

Currently installation of these scripts require access to the GDB "data directory" usually located at `/usr/share/gdb/python/gdb/command`.

## Usage

It is important that before a program is ran you initialise the debugging support with the `sacinit` command.

When you wish to convert a SAC variable or function identifier into it's C counterpart then you use the `*sac(variableName)` or `*sac(functionName())` commands.

## Examples

`print *sac(x)`

`breakpoint *sac(foo())`