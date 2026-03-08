# https://just.systems/man/en/

# SETTINGS

set dotenv-load := true

# Set shell based on OS
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
set shell := ["bash", "-cu"]

# VARIABLES

PACKAGE := "transcriber"
SOURCES := "src"
TESTS := "tests"

# DEFAULTS

# display help information
default:
    @just --list

# IMPORTS

import 'tasks/check.just'
import 'tasks/clean.just'
import 'tasks/commit.just'
import 'tasks/format.just'
import 'tasks/install.just'
import 'tasks/test.just'
import 'tasks/secrets.just'
import 'tasks/ui.just'
