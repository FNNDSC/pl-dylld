# Leg-Length Discrepency - Dynamic Compute Flow

[![Version](https://img.shields.io/docker/v/fnndsc/pl-dylld?sort=semver)](https://hub.docker.com/r/fnndsc/pl-dylld)
[![MIT License](https://img.shields.io/github/license/fnndsc/pl-dylld)](https://github.com/FNNDSC/pl-dylld/blob/main/LICENSE)
[![ci](https://github.com/FNNDSC/pl-dylld/actions/workflows/ci.yml/badge.svg)](https://github.com/FNNDSC/pl-dylld/actions/workflows/ci.yml)

`pl-dylld` is a [_ChRIS_](https://chrisproject.org/)
_ds_ plugin which connects to a parent node containing DICOM images and then dynamically creates a responsive compute flow (including joins). In its output directory, `pl-dylld` generates various logging/tracking data.


The documentation for entire LLD workflow along with step by step data flow in each of the compute nodes can be found here https://github.com/FNNDSC/CHRIS_docs/blob/master/workflows/LLD.md

## Abstract

Automatically calculating the lengths of human legs from XRay images can substantially improve radiological diagnosis time.

## Installation

`pl-dylld` is a _[ChRIS](https://chrisproject.org/) plugin_, meaning it can
run from either within _ChRIS_ or the command-line.

[![Get it from chrisstore.co](https://ipfs.babymri.org/ipfs/QmaQM9dUAYFjLVn3PpNTrpbKVavvSTxNLE5BocRCW1UoXG/light.png)](https://chrisstore.co/plugin/pl-dylld)

## Local Usage

To get started with local command-line usage, use [Apptainer](https://apptainer.org/)
(a.k.a. Singularity) to run `pl-dylld` as a container:

```shell
singularity exec docker://fnndsc/pl-dylld dylld [--args values...] input/ output/
```

To print its available options, run:

```shell
singularity exec docker://fnndsc/pl-dylld dylld --help
```

## Examples

`dylld` requires two positional arguments: a directory containing
input data, and a directory where to create output data.
First, create the input directory and move input data into it.

```shell
mkdir incoming/ outgoing/
mv some.dat other.dat incoming/
singularity exec docker://fnndsc/pl-dylld:latest dylld [--args] incoming/ outgoing/
```

## Development

Instructions for developers.

### Building

Build a local container image:

```shell
docker build -t localhost/fnndsc/pl-dylld .
```

### Running

Mount the source code `dylld.py` into a container to try out changes without rebuild.

```shell
docker run --rm -it --userns=host  \
    -v $PWD/dylld.py:/usr/local/lib/python3.11/site-packages/dylld.py:ro \
    -v $PWD/control:/usr/local/lib/python3.11/site-packages/control:ro \
    -v $PWD/logic:/usr/local/lib/python3.11/site-packages/logic:ro \
    -v $PWD/state:/usr/local/lib/python3.11/site-packages/state:ro \
    -v $PWD/in:/incoming:ro -v $PWD/out:/outgoing:rw -w /outgoing \
    localhost/fnndsc/pl-dylld dylld /incoming /outgoing
```

### Testing

Run unit tests using `pytest`.
It's recommended to rebuild the image to ensure that sources are up-to-date.
Use the option `--build-arg extras_require=dev` to install extra dependencies for testing.

```shell
docker build -t localhost/fnndsc/pl-dylld:dev --build-arg extras_require=dev .
docker run --rm -it localhost/fnndsc/pl-dylld:dev pytest
```

## Release

Steps for release can be automated by [Github Actions](.github/workflows/ci.yml).
This section is about how to do those steps manually.

### Increase Version Number

Increase the version number in `setup.py` and commit this file.

### Push Container Image

Build and push an image tagged by the version. For example, for version `1.2.3`:

```
docker build -t docker.io/fnndsc/pl-dylld:1.2.3 .
docker push docker.io/fnndsc/pl-dylld:1.2.3
```

### Get JSON Representation

Run [`chris_plugin_info`](https://github.com/FNNDSC/chris_plugin#usage)
to produce a JSON description of this plugin, which can be uploaded to a _ChRIS Store_.

```shell
docker run --rm localhost/fnndsc/pl-dylld:dev chris_plugin_info > chris_plugin_info.json
```

