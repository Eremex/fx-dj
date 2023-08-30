#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Eremex FX-DJ Static dependency injection tool for C/C++
#-------------------------------------------------------------------------------
# Copyright (c) JSC EREMEX 2010-2020.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the company nor the names of any co-contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE EREMEX. AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#-------------------------------------------------------------------------------

import os, re, sys, glob, subprocess, shutil, os.path, string, argparse

#-------------------------------------------------------------------------------
# Getting list of files, filtered by file extension.
# @param files List of files to be filtered by extension.
# @param ext Target file extension (in example '.c' or '.S').
# @return List of files found in specified directories

def fx_dj_filter_ext(files, ext):
    return list(filter(lambda path: os.path.splitext(path)[1] == ext, files))

#-------------------------------------------------------------------------------
# Gets exported entities by filename and regex.
# @param filename Path to file to be tested.
# @param empty_prepr_cmd Preprocessor command line in format (cmd %s), where %s
# is an input file.
# @param regexp Regular expression to be found in target file, should contain at
# least two groups (for interface and implementation).
# @return Tuple ((interface, implementation), filename).

def fx_dj_get_exports(filename, empty_prepr_cmd, regexp):
    with open(filename, 'r') as f:
        export = re.search(regexp, f.read())
        if export is not None:
            return ((export.group(1), export.group(2)), filename)
    return (tuple(), filename)

#-------------------------------------------------------------------------------
# Gets dictionary[interface] = filename.
# @param headers List of headers (strings, representing paths to headers).
# @param empty_prepr_cmd Preprocessor command line for file preprocessing.
# @return List of entities (exported_interface_list, filename).

def fx_dj_get_interfaces(headers, empty_prepr_cmd):
    dic = {}
    for filename in headers:
        exports, header_name = fx_dj_get_exports(
            filename,
            empty_prepr_cmd,
            'FX_METADATA\(\(\{\s*interface:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\]\s+\}\)\)'
        )
        if len(exports) > 0:
            if exports not in dic:
                dic[exports] = header_name
            else:
                raise Exception('Interface duplication %s %s %s' %
                    (exports, dic[exports], header_name))
    return dic

#-------------------------------------------------------------------------------
# Gets list of tuples (exported_implementations_list, filename) by filename.
# @param sources List of source files (strings, representing paths to sources).
# @param empty_prepr_cmd Preprocessor command line for file preprocessing.
# @return List of entities like (exported_implementations_list, filename).

def fx_dj_get_implementations(sources, empty_prepr_cmd):
    exports = [
        fx_dj_get_exports(
            s,
            empty_prepr_cmd,
            'FX_METADATA\(\(\{\s*implementation:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\]\s+\}\)\)'
        ) for s in sources
    ]
    return list(filter(lambda item: len(item[0]) != 0, exports))

#-------------------------------------------------------------------------------
# Gets list of tuples (default_interface, implementation) by alias file.
# @param linkage Path to alias file, containing implementation to interface map.
# @return List of entities like (default_interface_name, implementation_name).

def fx_dj_get_aliases(linkage):
    aliases = []
    with open(linkage, 'r') as f:
        aliases = re.findall('(\w+)\s+=\s+(\w+)', f.read())
    return aliases

#-------------------------------------------------------------------------------
# Creates root interface file, which should be included in all compile entities.
# @param root Path to root interface file.
# @param ifces List of interfaces found in header files as (interfaces, file).
# @parama aliases List of aliases extracted from mapping file: (interface,impl).
# @return None.

def fx_dj_generate_root_header(root, ifces, aliases):
    pfx     = 'INTERFACE____'
    header  = ['#ifndef __ROOT__\n#define __ROOT__\n\n']
    notes   = ['//This file is automatically generated, DO NOT EDIT!\n']
    predefs = ['#define ____INTERFACE(I) INTERFACE____##I \n\n',
               '#define FX_INTERFACE(I) ____INTERFACE(I) \n\n']
    footer  = ['#endif\n']

    defs = [ '#define\t %s \"%s\" \n' %
        (pfx + i + '____' + impl,path) for ((i,impl),path) in ifces.items()]

    i2impl = {}
    for x in ifces.items():
        i2impl.setdefault(x[0][0], []).append(x[0][1])

    explicit = [ '#define\t %s \t\t %s \n' %
        (pfx + i, pfx + i + '____' + impl) for (i, impl) in aliases ]

    implicit = [ '#define\t %s \t\t %s \n' %
        (pfx + k, pfx + k + '____' + v[0])
            for (k,v) in i2impl.items() if len(v)==1 and k not in explicit ]

    result = header + notes + predefs + defs + explicit + implicit + footer
    with open(root, 'w+') as root_file:
        for line in result:root_file.write(line)

#-------------------------------------------------------------------------------
# Get list of dependencies by source file name.
# @param f Path to source file.
# @param r Root interface file (which contains interface 2 impl mapping).
# @param cmd Command line which is used as C preprocessor with force include.
# @return List of dependencies of specified file.

def fx_dj_get_dependencies(f, r, cmd):
    stdout = str(subprocess.check_output(cmd % (r, f), shell=True))
    return re.findall(
        'FX_METADATA\(\(\{\s*interface:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\]\s+\}\)\)',
        stdout
    )

#-------------------------------------------------------------------------------
# Getting sources to be built by dependency graph and target interface.
# @param dep Dependency graph, represented as hashmap d[key] = val, where key is
# equal to interface name and value is equal to tuple:
# (list of files implementing interface, dependencies, "already processed" flag)
# Flag is needed in order to prevent infinite cycles in case of cross-deps.
# @param targets Target interface to be built. It is equal to user-specified
# target interface for first-time call (list with one item).
# @param objs Files to be built in order to implement target interface.
# @return None.

def fx_dj_get_sources_by_graph(dep, targets, objs, gd):
    for target in targets:
        if target not in dep:
            dep[target] = ([], [], True)
            continue
        files, dependencies, already_processed = dep[target]
        if already_processed is False:
            dependencies = gd(files)
            dep[target] = (files, dependencies , True)
            objs.extend(files)
            fx_dj_get_sources_by_graph(dep, dependencies, objs, gd)

#-------------------------------------------------------------------------------
# Simple test of C preprocessor, which is passed as command line.
# @param cmd_line Command line which is used to call preprocessor.
# It receives two arguemtns: force include file and file to be preprocessed.
# @return True if preprocessor test is passed, False otherwise.

def fx_dj_test_preprocessor(cmd_line):
    stdout = ''
    tmp_src = open('tmp_src.c', 'w')
    tmp_src.write('TEST\n')
    tmp_src.close()
    tmp_hdr = open('tmp_hdr.h', 'w')
    tmp_hdr.write('#define TEST PASSED\r')
    tmp_hdr.close()
    stdout = str(subprocess.check_output(
        cmd_line % (tmp_hdr.name, tmp_src.name),
        shell=True
    ))
    os.remove('tmp_src.c')
    os.remove('tmp_hdr.h')
    return (stdout.find('PASSED') != -1)

#-------------------------------------------------------------------------------
#--MAIN-SCRIPT-CODE-------------------------------------------------------------
# Create parser of command line parameters.
#
parser = argparse.ArgumentParser(description='Eremex FX-DJ v1.9')
parser.add_argument('-p', dest='p', required=True, metavar='Path',
    help='interface sources path')
parser.add_argument('-t', dest='target', required=True, metavar='Target',
    help='target interface to be built')
parser.add_argument('-a', dest='alias', required=True, metavar='Alias',
    help='default interfaces to implementation mapping')
parser.add_argument('-o',  dest='o', metavar='Sources', default='sources',
    help='list of sources to be built')
parser.add_argument('-m',  dest='common_hdr', metavar='Hdr', default='map.tmp',
    help='common header for dependency injection (must be included in sources)')
parser.add_argument('-l', dest='sdk', metavar='SDK', default=None,
    help='enables generation of common header for SDK')
parser.add_argument('-v', dest='v', action='store_true',
    help='enables verbose')
parser.add_argument('-I', dest='I', metavar='Include_dir', default=None,
    help='specify base folder for include paths in generated headers')

#-------------------------------------------------------------------------------
# Parse arguments.
#
args = parser.parse_args()

#-------------------------------------------------------------------------------
# Check paths.
#
src_paths = args.p.split(',')

for p in src_paths:
    if os.path.exists(p) == False:
        print('Incorrect path passed as parameter')
        exit(1)

if args.v is True:
    print('\nSource paths:\n')
    for p in src_paths:
        print (os.path.abspath(p))

#-------------------------------------------------------------------------------
# Check the preprocessor.
#
prepr_cmd = ''
try:
    prepr_cmd = os.environ['FX_PREP']
    if fx_dj_test_preprocessor(prepr_cmd) == False:
        print('Incorrect preprocessor command line')
        exit(1)
except:
    print('Invalid preprocessor! (check \'FX_PREP\' environment variable)')
    exit(1)

#-------------------------------------------------------------------------------
# Convert paths to absolute and get list of files.
#
src_dir = map(lambda f: os.path.abspath(f), src_paths)
abs_src_dirs = []
for folder in src_dir:
    if sys.version_info.major > 2:
        for root, dirs, files in os.walk(folder):
            abs_src_dirs.extend( [os.path.join(root, f) for f in files] )
    else:
        os.path.walk(
            folder,
            lambda arg, dir, files:
                arg.extend( [os.path.join(dir, f) for f in files] ),
            abs_src_dirs
        )
files = list(filter(lambda pathname: os.path.isfile(pathname), abs_src_dirs))

#-------------------------------------------------------------------------------
# Get all headers.
#
headers = fx_dj_filter_ext(files, '.h')

if args.v is True:
    print('\nInterface headers:\n')
    for h in headers:
        print(os.path.abspath(h))

# Not used, but saved as a parameter for possible further changes.
#
empty_prepr_cmd = ''

#-------------------------------------------------------------------------------
#Get interfaces from headers.
#
interfaces = fx_dj_get_interfaces(headers, empty_prepr_cmd)

if args.v is True:
    print('\nInterface headers:\n')
    for i,f in interfaces.items():
        print ('%s : %s' % (i, f))

#-------------------------------------------------------------------------------
#Get aliases from mapping file.
#
aliases = fx_dj_get_aliases(args.alias)

#-------------------------------------------------------------------------------
# On some platforms there may be problems with absolute paths in common header.
# They may be fixed by using relative paths, in this case you should provide
# base include folder as a parameter (-I key). If the parameter is specified,
# all interface-header mappings are generated in relative form.
# __WARNING!!!__ BECAUSE PREPROCESSOR IS USED TO GET FILE DEPENDENCIES, IF YOU
# USE RELATIVE PATHS YOU SHOULD SET THE SAME FOLDER IN PREPROCESSOR COMMAND LINE
# (IN FX_PREP ENV. VARIABLE) FOR DEFAULT INCLUDE PATH!
#
interfaces_to_hdr_map = {}

if args.I is not None:
    if(os.path.exists(args.I)):
        for i, path in interfaces.items():
            interfaces_to_hdr_map[i] = os.path.relpath(path, args.I)
    else:
        print('Incorrect path passed as a base include path!')
        exit(1)
else:
    interfaces_to_hdr_map = interfaces

#-------------------------------------------------------------------------------
# Determine implemetation of target interface specified in command line.

target_impl = None
for (i, impl) in aliases:
    if i == args.target:
        target_impl = impl
        break
if target_impl == None:
    target_impls = [impl
        for (i, impl) in interfaces_to_hdr_map.keys() if i == args.target]
    if len(target_impls) == 0:
        print('No implementations found for target interface!')
        exit(1)
    if len(target_impls) > 1:
        print('Warning! There are multiple implementations for target')
    target_impl = target_impls[0]

#-------------------------------------------------------------------------------
# Get implementations from source folders.
#
impls = []

for d in ['.S','.c','.cpp']:
    srcs = fx_dj_filter_ext(files, d)
    impls.extend(fx_dj_get_implementations(srcs, empty_prepr_cmd))

if args.v is True:
    print('\nImplementations:\n')
    for (i_files, i_name) in impls:
        print ('%s : %s' % (i_name, ','.join(i_files)))

#-------------------------------------------------------------------------------
#Create root interface file.
#
root_file = os.path.abspath(args.common_hdr)
fx_dj_generate_root_header(root_file, interfaces_to_hdr_map, aliases)

#-------------------------------------------------------------------------------
# Create dependency graph (fill only interface->implementation_files mapping).
#
deps = {}
for impl_lst, src in impls:
    impl_file, depend, pr = deps.setdefault(impl_lst, ([], [], False))
    impl_file.append(src)

#-------------------------------------------------------------------------------
# Get files to be built into "output_files".
# This phase also fills dependency graph with dependencies.
# Lambda expression which return list of dependencies for list of files.
#
output_files = []
target_interface = (args.target, target_impl)

fx_dj_get_sources_by_graph(
    deps,
    [target_interface],
    output_files,
    lambda files:
        [d for f in files
            for d in fx_dj_get_dependencies("\"%s\"" % f, root_file, prepr_cmd)]
)

if args.v is True:
    print('\nDependencies:\n')
    for k, (_, dependencies, included) in deps.items():
        if included is True:
            processed_deps = map(lambda x: str(x[0] + ':' + x[1]), dependencies)
            print ('%s -> %s' % (str(k), ','.join(processed_deps)))

output_files = set(output_files)

#-------------------------------------------------------------------------------
#Generate output.

if os.path.exists(args.o) and os.path.isdir(args.o):
    def fx_dj_transform_filename(item):
        files = []
        j = 1
        for i in item[0]:
            filename = os.path.splitext(i)
            files.append(filename[0] + str(j) + filename[1])
            j = j + 1
        return (files, item[1])

    included_interfaces = {
        k for k, (_, _, included) in deps.items() if included == True
    }

    srcs_to_copy = []
    hdrs_to_copy = []
    files_map = {}
    translated_srcs = []

    for i in included_interfaces:
        (impls, _, _) = deps[i]
        srcs_to_copy.extend(impls)
        hdrs_to_copy.append(tuple(([i[0] + '.h'], [interfaces[i]])))

    for filepath in srcs_to_copy:
        _, filename = os.path.split(filepath)
        names, fpath = files_map.setdefault(filename, ([], []))
        names.append(filename)
        fpath.append(filepath)

    for k, v in files_map.items():
        files_with_same_name, _ = v
        if len(files_with_same_name) > 1:
            translated_srcs.append(fx_dj_transform_filename(v))
        else:
            translated_srcs.append(v)

    translated_srcs.extend(hdrs_to_copy)
    for fnames, fpaths in translated_srcs:
        for n, p in zip(fnames, fpaths):
            src = p
            dst = os.path.join(args.o, n)
            if args.v is True:
                print ('Copying %s to %s' % (src, dst))
            shutil.copyfile(src, dst)
else:
    with open(args.o, 'w+') as f:
        for src_file in output_files: f.write(src_file + '\n')

#-------------------------------------------------------------------------------
#Generate common header for SDK.
#
if args.sdk is not None:
    content = fx_dj_get_dependencies(
        interfaces[target_interface], root_file, prepr_cmd
    )
    with open(args.sdk, 'w+') as f:
        for i in content: f.write(i[0] + '\n')

print('Done. Output: %d source files.' % len(output_files))
