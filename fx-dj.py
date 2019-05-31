#----------------------------------------------------------------------------------------------------
# Eremex FX-DJ Static dependency injection tool for C/C++
#----------------------------------------------------------------------------------------------------
# Copyright (c) 2010-2019, Eremex Ltd.
# All rights reserved.
#
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
#    (including use for configuration) without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE EREMEX LTD. AND CONTRIBUTORS ``AS IS'' AND
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
#----------------------------------------------------------------------------------------------------

import os, re, sys, glob, subprocess as sp, shutil, os.path as osp, string, argparse, tempfile, copy

#----------------------------------------------------------------------------------------------------
# Getting files list by list of folders
# @param src_dirs List of directories to collect files from.
# @return List of files found in specified directories.

def fx_dj_get_all_files(src_dirs):
    arg = []
    for folder in src_dirs:
        osp.walk(folder, lambda arg, dir, files: arg.extend([osp.join(dir, f) for f in files]), arg)
    return filter(lambda pathname: osp.isfile(pathname), arg)

#----------------------------------------------------------------------------------------------------
# Getting list of files, filtered by file extension.
# @param files List of files to be filtered by extension.
# @param ext Target file extension (in example '.c' or '.S').
# @return List of files found in specified directories

def fx_dj_filter_ext(files, ext):
    def fx_dj_filter_ext_inner(file_path, file_ext):
        file_name, file_extnsion = osp.splitext(file_path)              #Get extension.
        return (file_extnsion == file_ext)                              #Return True is extensions
                                                                        #are equal.
    return filter(lambda path: fx_dj_filter_ext_inner(path, ext), files)

#----------------------------------------------------------------------------------------------------
# Ensures that specified dir exists. If directory is not exists it will be created.
# @param d Directory to be tested.
# @return None.

def fx_dj_ensure_dir(d):
    if not osp.exists(d):
        os.makedirs(d)

#----------------------------------------------------------------------------------------------------
# Gets exported entities by filename and regex.
# @param filename Path to file to be tested.
# @param empty_prepr_cmd Preprocessor command line in format (cmd %s), where %s is a input file.
# @param regexp Regular expression to be found in target file, should contain at least two groups 
#               (for interface and implementation).
# @return Tuple ((interface, implementation), filename).

def fx_dj_get_exports(filename, empty_prepr_cmd, regexp):   #Internal function getting list of exported interfaces

    return_value = (tuple(), filename)

    with open(filename, 'r') as f:
        export = re.search(regexp, f.read())
        if export is not None:
            return_value = ((export.group(1), export.group(2)), filename)

    return return_value                         
    
#----------------------------------------------------------------------------------------------------
# Gets dictionary[interface] = filename.
# @param headers List of headers (strings, representing paths to headers).
# @param empty_prepr_cmd Preprocessor command line for file preprocess before metadata extraction.
# @return List of entities (exported_interface_list, filename).

def fx_dj_get_interfaces(headers, empty_prepr_cmd):

    dic = {}
    
    #Get list of exported interfaces linked with filename.
    def fx_dj_get_interfaces_internal(filename):
        exports, header_name = fx_dj_get_exports(
            filename,
            empty_prepr_cmd, 
            'FX_METADATA\(\(\{\s*interface:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\].*\}\)\)')

        if len(exports) > 0:
            if exports not in dic:
                dic[exports] = header_name
            else:
                raise Exception('Interface duplication %s %s %s' % (exports, dic[exports], header_name))

    #Fill dictionary by mapping function over headers list.
    map(fx_dj_get_interfaces_internal, headers)
    return dic

#----------------------------------------------------------------------------------------------------
# Gets list of tuples (exported_implementations_list, filename) by filename.
# @param sources List of source files (strings, representing paths to sources).
# @param empty_prepr_cmd Preprocessor command line for file preprocess before metadata extraction.
# @return List of entities like (exported_implementations_list, filename).

def fx_dj_get_implementations(sources, empty_prepr_cmd):

    #Get list of exported implementations linked with filename.
    def fx_dj_get_implementations_internal(filename):
        return fx_dj_get_exports(
            filename, 
            empty_prepr_cmd,
            'FX_METADATA\(\(\{\s*implementation:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\].*\}\)\)')

    #Filtering function: skip file if it is exporting no implementations.
    def fx_dj_continaing_implementations(list_item):
        impls, filename = list_item
        return (len(impls) != 0)
    
    return filter(fx_dj_continaing_implementations, map(fx_dj_get_implementations_internal, sources))

#----------------------------------------------------------------------------------------------------
# Gets list of tuples (default_interface, implementation) by alias file.
# @param linkage Path to alias file, containing implementation to default interface mappings.
# @return List of entities like (default_interface_name, implementation_name). 

def fx_dj_get_aliases(linkage):
    aliases = []
    
    if linkage:
        #Get file content.
        with open(linkage, 'r') as f: aliases = re.findall('(\w+)\s+=\s+(\w+)', f.read())

    #Get list of pairs (default interface name, implementation name).
    return aliases

#----------------------------------------------------------------------------------------------------
# Creates root interface file, which should be included in all compile entities.
# @param root Path to root interface file.
# @param ifces List of interfaces found in header files (like (list of interfaces, filename)).
# @parama aliases List of aliases extracted from mapping file (like (default_intrfce, implementtion).
# @return None.

def fx_dj_generate_root_interface_file(root, ifces, aliases):

    #Set predefines.
    pfx     = 'INTERFACE____'
    header  = ['#ifndef __ROOT__\n#define __ROOT__\n\n']

    notes   = ['//This file is automatically generated, DO NOT EDIT!\n',
               '//This file MUST be implicitly included in all sources:\n',
               '//\tFor Microsoft use \"-FI<path to this file>\" command line option,\n',
               '//\tFor GCC use \"-include <path to this file>\" command line option\n',
               '\n\n']
    
    predefs = ['#define ____INTERFACE(I) INTERFACE____##I \n\n',
               '#define FX_INTERFACE(I) ____INTERFACE(I) \n\n',
			   '#ifndef FX_DJ_PREPROCESS_STAGE \n\n',
			   '#define FX_METADATA(x) \n\n',
			   '#endif \n\n']
    
    footer  = ['#endif\n']

    impl_num = {}

    #Get interface to filename mapping.
    defs = []
    for i, path in ifces.iteritems():
            intrface, impl = i
            impl_num.setdefault(intrface, []).append(impl)
            defs.append('#define\t %s \"%s\" \n' % (pfx + intrface + '____' + impl, path))

    #Get default interface to implementation mapping.
    mapping = []
    for default_intrface, impl in aliases:
        mapping.append('#define\t %s \t\t %s \n' % (pfx + default_intrface, pfx + default_intrface + '____' + impl))

    for k, v in impl_num.iteritems():
        if len(v) == 1:
            mapping.append('#define\t %s \t\t %s \n' % (pfx + k, pfx + k + '____' + v[0]))

    #Generate root interface file.
    result = header + notes + predefs + defs + mapping + footer

    #Store it to file.
    with open(root, 'w+') as root_file: 
        for line in result: root_file.write(line)

#----------------------------------------------------------------------------------------------------
# Get list of dependencies by source file name.
# @param f Path to source file.
# @param r Root interface file (which contains interface2implementation mapping).
# @param cmd Command line which is used as C preprocessor with force include.
# @return List of dependencies of specified file.

def fx_dj_get_dependencies(f, r, cmd):
    #Preprocess file with specified command line.
    p = sp.Popen(cmd % (r, f), stdout=sp.PIPE, stderr=sp.PIPE, shell=True)

    #Get output.
    stdout, stderr = p.communicate()

    if p.returncode != 0:
        print 'Warning! Preprocessing error in file: %s\n' % f
        print stderr
        exit(1)
    
    #Get all interfaces from preprocessed file (all included headers, contaning interfaces).
    d = re.findall('FX_METADATA\(\(\{\s*interface:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\].*\}\)\)', stdout)

    return d

#----------------------------------------------------------------------------------------------------
# Getting sources to be built by dependency graph and target interface.
# @param dep Dependency graph, represented as hashmap d[key] = val, where key is equal to interface
#            name and value is equal to tuple:
#            (list of files implementing interface, dependencies, "already processed" flag). Flag is
#            needed in order to prevent infinite cycles in case of cross-dependencies.
# @param targets Target interface to be built. It is equal to user-specified target interface for
#                first-time call (list with one item).
# @param objs Files to be built in order to implement target interface.
# @return None.

def fx_dj_get_sources_by_graph(dep, targets, objs, gd):
    for target in targets:                                  #For each target.
        if target not in dep: 
            dep[target] = ([], [], True)
            continue
        files, dependencies, already_pr = dep[target]
        if already_pr is False:                             #Skip if interface is already processed.
            dependencies = gd(files)
            dep[target] = (files, dependencies , True)      #Mark interface as already processed.
            objs.extend(files)                              #Save files implementing target interface.
                                                            #Recursive call for all dependencies.
            fx_dj_get_sources_by_graph(dep, dependencies, objs, gd)
            
#----------------------------------------------------------------------------------------------------
# Simple test of C preprocessor, which is passed as command line.
# @param cmd_line   Command line which is used to call preprocessor.
#                   It receives two arguemtns: force include file and file to be preprocessed.    
# @return True if preprocessor test is passed, False otherwise.

def fx_dj_test_preprocessor(cmd_line):
        #Create two temp files, for fake header and source.
        tmp_src = tempfile.NamedTemporaryFile(suffix='.c', delete=False, dir='.')
        tmp_hdr = tempfile.NamedTemporaryFile(suffix='.h', delete=False, dir='.')

        #Write test #define into header and use it in source.
        tmp_src.write('TEST\n')
        tmp_hdr.write('#define TEST PASSED\r')

        #Close both files. Now they are available for third-party tools.
        tmp_src.close() 
        tmp_hdr.close()

        #Call preprocessor for temporary files and save output.
        p = sp.Popen(cmd_line % (tmp_hdr.name, tmp_src.name), stdout=sp.PIPE, stderr=sp.PIPE, shell=True)
        stdout, stderr = p.communicate()

        if p != 0:
            print stderr

        #Remove temporary files.
        os.remove(tmp_hdr.name)
        os.remove(tmp_src.name)

        #Return True if preprocessor replaced macros in our temp source.
        return (stdout.find('PASSED') != -1)

#----------------------------------------------------------------------------------------------------
# Check for all paths passed as parameters exist.
# @param paths  List of paths to folders.
# @return True if all specified paths are exist, False otherwise.

def fx_dj_check_paths(paths):
    for p in paths:
        if osp.exists(p) == False:
            return False
    return True

#----------------------------------------------------------------------------------------------------
# Getting common prefix of filenames list.
# @param files_list List of strings representing filenames.
# @return String representing common prefix.

def fx_dj_common_prefix(files_list):
    common_pfx = osp.commonprefix(files_list)
    if osp.exists(common_pfx) is False:
        common_pfx = osp.dirname(common_pfx) + '/'
    return common_pfx

#----------------------------------------------------------------------------------------------------
# Getting constructor info from interface header.
# @param h String representing path to a header file.
# @return tuple (func, type) where func is a the contructor name, type is "on_boot_cpu" or "on_each_cpu".

def fx_dj_get_ctor_info(h, prepr_cmd_line):
    ret = None

    with open(h, 'r') as f:
        res = re.search('FX_METADATA\(\(\{.*ctor:\s+\[\s*(\w+)\s*,\s*(\w+)\s*\].*\}\)\)', f.read())
        if res is not None:
            ret = (res.group(1), res.group(2))

    return ret

#----------------------------------------------------------------------------------------------------
# Building initialization graph by dependency graph built by fx_dj_get_sources_by_graph.
# @param deps Dependency graph deps[interface_name] = ([src_files], [dependencies_list], included).
# @param hdr_map Dictionary which maps interface to header name.
# @return Initialization graph as a dictionary:
#         init_graph[interface] = ([dependencies], open/close node, processed, init_order, ctor_info)
#         where dependencies is a set of keys in the same dictionary, open/close, processed and 
#         init_order are used later on second phase. Ctor_info is a tuple (ctor_name, ctor_type).

def fx_dj_build_init_graph(deps, hdr_map, prepr_cmd_line):
    init_gr = {}

    #Walk through dependency graph and get constructor info for interfaces which are included.
    #(These interfaces have True in the "included" flag).
    #After this cycle completed we have init_gr filled with interfaces need to be initialized
    #and have dependencies and constructor info about each of them.

    for k,( _, dependencies, included) in deps.items():
        if included is True:
            h = fx_dj_get_ctor_info(hdr_map[k], prepr_cmd_line)
            if h is not None: init_gr[k] = (dependencies, False, False, 0, h)

    #Note that dependencies were copied directly from dependency graph and contain all dependent
    #interfaces. Next stage is removing interfaces which has no contructors from dependencies.
    #Also we set "processed" flag for items which has no dependencies (they have init order 0).
    
    for k in init_gr.keys():
        dps, _, _, _, ctor_info = init_gr[k]
        if len(dps) != 0:

            #Exclude duplicates, dependencies which are not needed to be initialized and
            #dependencies from itself.
            
            d = set(filter(lambda x: x in init_gr.keys() and (x != k), dps))
            init_gr[k] = (d, False, False, 0, ctor_info)        
        else:
            init_gr[k] = ([], False, True, 0, ctor_info)
    return init_gr

#----------------------------------------------------------------------------------------------------
# Calculation of init order for each init graph node.
# @param init_graph Initialization graph.
# @param target String representing target interface.
# @return Init order for specified node (corresponding to the target).

def fx_dj_build_init_info(init_graph, target):
    maximum = 0

    #Get node corresponding to the target.
    dependencies, open_sw, processed_sw, order_num, ctr_info = init_graph[target]

    #Before each recursive call node is marked as 'opened', if we come to such node it mean
    #that init graph loop exists and initialization sequence cannot be calculated.
    if open_sw is True: raise Exception('Initialization graph loop detected! %s' % t)

    #If node is already processed just return init order number, otherwise walk through
    #dependencies and set init order as maximum between all child nodes + 1.
    if processed_sw is False:

        #Mark node as 'opened'.
        init_graph[target] = (dependencies, True, False, order_num, ctr_info)

        #Recursive call for each child node and determining maximum.
        for t in dependencies:
            ordr = fx_dj_build_init_info(init_graph, t) + 1
            if ordr > maximum: maximum = ordr

        #Mark node as 'closed' and 'already processed'.
        init_graph[target] = (dependencies, False, True, maximum, ctr_info)
    else:
        maximum = order_num
    return maximum

#----------------------------------------------------------------------------------------------------
# Getting initialization sequence.
# @param deps Dependencies graph.
# @param hdr_map Dictionary which maps interface name to interface header.
# @return Sequence (ctor_name, ctor_type).

def fx_dj_get_init_sequence(deps, hdr_map, prepr_cmd_line):

    #Build initialization dependencies from dependency graph.
    init_gr = fx_dj_build_init_graph(deps, hdr_map, prepr_cmd_line)

    #Calculate initialization sequence for each graph node.
    for k in init_gr.keys(): fx_dj_build_init_info(init_gr, k)

    #Sort graph nodes by init order.
    constructor_sequence_temp = sorted(init_gr.values(), key = lambda x: x[3]) 

    #Remove service info from graph.
    constructor_sequence = map(lambda x: (x[4]), constructor_sequence_temp)

    return constructor_sequence

#----------------------------------------------------------------------------------------------------
# Generation of initialization sequence.
# @param init_file PAth to the initialization source file.
# @param deps Dependency graph.
# @param hdr_map Dictionary which maps interface name to interface header.
# @param target Target interface.
# @return Absolute path to initialization source (to be included into makefile).

def fx_dj_generate_ctor_file(init_file, deps, hdr_map, target, prepr_cmd_line):

    intrface, impl = target.split(":")

    init_seq = fx_dj_get_init_sequence(deps, hdr_map, prepr_cmd_line)

    #Set presence of ctor-file.
    i_file = osp.abspath(init_file)
    
    #Flush initialization file.
    with open(init_file, 'w+') as init_f:

        #Write standard header.
        init_f.write('// Automatically generated file. Initialization sequence.\n\n\
                      #include FX_INTERFACE(%s)\n\n\
                      void fx_dj_init_once()\n{\n' % intrface)

        #Write constructor sequence.
        for (ctor_name, _) in init_seq: init_f.write('\t%s();\n' % ctor_name)
        init_f.write('}\n')

        ap_init = filter(lambda x: x[1] == 'on_each_cpu', init_seq)
        init_f.write('\n\nvoid fx_dj_init_each()\n{\n')

        for (ctor_name, _) in ap_init: init_f.write('\t%s();\n' % ctor_name)
        init_f.write('}\n')

    return i_file   


#----------------------------------------------------------------------------------------------------
#--MAIN-SCRIPT-CODE----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------    
#
#Create parser of command line parameters.
#    
parser = argparse.ArgumentParser(description='Eremex FX-DJ v1.6')

#---------------------------------------------------------------------------------------------------- 
#
#Adjust arguments.
# 
parser.add_argument('-a',  dest='alias', metavar='Alias',
                    help='default \"interfaces to implementation\" mapping')
parser.add_argument('-t',  dest='target', required=True, metavar='Target',
                    help='target interface to be built')
parser.add_argument('-c',  dest='common_header', metavar='Header', default='mapping.h',
                    help='common header for dependency injection (should be included in all sources)')
parser.add_argument('-o',  dest='o', metavar='Sources', default='sources',
                    help='list of sources to be built')
parser.add_argument('-p',  dest='p', metavar='Path', nargs='+',
                    help='interface sources path')
parser.add_argument('-pf', dest='pf', metavar='Pathfile',
                    help='path to file containing interface paths')
parser.add_argument('-i',  dest='ctors', metavar='Ctors', default=None,
                    help='enables generation of initialization sequence')
parser.add_argument('-s', dest='sdk', metavar='SDK', default=None,
                    help='enables generation of common header for SDK')
parser.add_argument('-v', dest='v', action='store_true',
                    help='enables verbose')
parser.add_argument('-I', dest='I', metavar='Include_dir', default=None,
                    help='specify base folder for include paths in generated headers')

#----------------------------------------------------------------------------------------------------
#Parse arguments.
#
args = parser.parse_args()

#----------------------------------------------------------------------------------------------------
#Check paths.
#
if fx_dj_check_paths(args.p) == False:
    print 'Incorrect path passed as parameter'
    exit(1)

if args.v is True:
    print '\nSource paths:\n'
    for p in args.p:
        print osp.abspath(p)

#----------------------------------------------------------------------------------------------------
#Check preprocessor.
#
prepr_cmd_line = ''
try:
    prepr_cmd_line = os.environ['FX_PREP']
    if fx_dj_test_preprocessor(prepr_cmd_line) == False:
        print 'Incorrect preprocessor command line'
        exit(1)
except:
    print 'Invalid preprocessor! (check \'FX_PREP\' environment variable)'
    exit(1)

#----------------------------------------------------------------------------------------------------
#Convert paths to absolute and get list of files.
#
src_dir = map(lambda f: osp.abspath(f), args.p)
files = fx_dj_get_all_files(src_dir)

#----------------------------------------------------------------------------------------------------
#Get all headers.
#
headers = fx_dj_filter_ext(files, '.h')

if args.v is True:
    print '\nAll headers:\n'
    for h in headers:
        print osp.abspath(h)

#
# Obsolete argument. Not used, but saved as a parameter for possible further changes.
#        
empty_prepr_cmd = ""

#----------------------------------------------------------------------------------------------------
#Get interfaces from headers.
#

interfaces = fx_dj_get_interfaces(headers, empty_prepr_cmd)

if args.v is True:
    print '\nInterface headers:\n'
    for i,f in interfaces.iteritems():
        print ('%s : %s' % (i, f))

#impls_dic = {}
#for (i, im) in interfaces.keys():
#    temp = impls_dic.setdefault(i, [])
#    temp.append(im)
#filtered_impls = dict((k, v) for k, v in impls_dic.iteritems() if len(v) == 1)

#----------------------------------------------------------------------------------------------------
#Get aliases from mapping file.
#
aliases = fx_dj_get_aliases(args.alias)

#----------------------------------------------------------------------------------------------------
#On some platforms there may be problems with absolute paths in common header. They may be fixed by
#using relative paths, in this case you should provide base include folder as a parameter (-I key).
#If the parameter is specified, all interface-header mappings are generated in relative form.
#__WARNING!!!__ BECAUSE PREPROCESSOR IS USED TO GET FILE DEPENDENCIES, IF YOU USE RELATIVE PATHS
#YOU SHOULD SET THE SAME FOLDER IN PREPROCESSOR COMMAND LINE (IN FX_PREP ENV. VARIABLE) FOR 
#DEFAULT INCLUDE PATH!
#
interfaces_to_hdr_map = {}

if args.I is not None:
    if(osp.exists(args.I)):
        for i, path in interfaces.iteritems():
            interfaces_to_hdr_map[i] = osp.relpath(path, args.I)
    else:
        print 'Incorrect path passed as a base include path!'
        exit(1)
else:
    interfaces_to_hdr_map = interfaces

#----------------------------------------------------------------------------------------------------
#Get implementations from source folders.
#
impls = []

for d in ['.S','.c','.cpp']:
    srcs = fx_dj_filter_ext(files, d)
    impls.extend(fx_dj_get_implementations(srcs, empty_prepr_cmd))

if args.v is True:
    print '\nImplementations:\n'
    for (i_files, i_name) in impls:
        print ('%s : %s' % (i_name, ','.join(i_files)))

#----------------------------------------------------------------------------------------------------
#Create root interface file.
#
root_file = osp.abspath(args.common_header)
fx_dj_generate_root_interface_file(root_file, interfaces_to_hdr_map, aliases)

#----------------------------------------------------------------------------------------------------
#Create dependency graph (fill only interface->implementation_files mapping).
#Dependencies will be filled during dependency injection.    
#
deps = {}

for impl_lst, src in impls:
    impl_file, depend, pr = deps.setdefault(impl_lst, ([], [], False))
    impl_file.append(src)

#----------------------------------------------------------------------------------------------------
#Get files to be built into "output_files". This phase also fills dependency graph with dependencies.
#

output_files = []
target_interface = tuple(args.target.split(':'))

fx_dj_get_sources_by_graph(
    deps,                           #Dependency graph.
    [target_interface],             #Target interface specified by user.
    output_files,                   #Resulting list of files to be built.
    lambda files: [x                #Lambda expression which return list of dependencies for list of files.
                   for f in files
                       for x in fx_dj_get_dependencies("\"%s\"" % f, root_file, prepr_cmd_line)])

if args.v is True:
    print '\nDependencies:\n'
    for k, (_, dependencies, included) in deps.iteritems():
        if included is True:
            processed_deps = map(lambda (x, y): str(x + ':' + y), dependencies)
            print ('%s -> %s' % (str(k), ','.join(processed_deps)))

#----------------------------------------------------------------------------------------------------
#Create initialization sequence based on header dependencies.
#

i_file = None

if args.ctors is not None:
    i_file = fx_dj_generate_ctor_file(args.ctors, deps, interfaces, args.target, prepr_cmd_line)

# Append initialization sequence file to output files list (if present).
if i_file is not None:  output_files.append(i_file)

#----------------------------------------------------------------------------------------------------
#Generate requested output

# Remove duplicates from output.
output_files = set(output_files)

#----------------------------------------------------------------------------------------------------
#Generate output.

if osp.exists(args.o) and osp.isdir(args.o):

    def fx_dj_transform_filename(item):
        files = []
        j = 1
        for i in item[0]:
            filename = osp.splitext(i)
            files.append(filename[0] + str(j) + filename[1])
            j = j + 1
        return (files, item[1])

    included_interfaces = { k for k, (_, _, included) in deps.iteritems() if included == True }

    srcs_to_copy = []
    hdrs_to_copy = []

    files_map = {}
    translated_srcs = []

    for i in included_interfaces:
        (impls, _, _) = deps[i]
        srcs_to_copy.extend(impls)
        hdrs_to_copy.append(tuple(([i[0] + '.h'], [interfaces[i]])))

    for filepath in srcs_to_copy:
        _, filename = osp.split(filepath)
        names, fpath = files_map.setdefault(filename, ([], []))
        names.append(filename)
        fpath.append(filepath)

    for k, v in files_map.iteritems():
        files_with_same_name, _ = v
        if len(files_with_same_name) > 1: 
            translated_srcs.append(fx_dj_transform_filename(v))
        else:
            translated_srcs.append(v)

    translated_srcs.extend(hdrs_to_copy)

    for fnames, fpaths in translated_srcs:
        for n, p in zip(fnames, fpaths):
            src = p
            dst = osp.join(args.o, n)
            print ('Copying %s to %s' % (src, dst))
            shutil.copyfile(src, dst)  
else:
    #Flush output file.
    #
    srcs_file = osp.abspath(args.o)
    fl = open(srcs_file, 'w+')
    fl.close() 
    
    #Generate output.   
    fl = open(srcs_file, 'a+')  
    for src_file in output_files: fl.write(src_file + '\n') #Store flat list of sources.
    fl.close()

#----------------------------------------------------------------------------------------------------
#Generate common OS header for SDK.
#

if args.sdk is not None:
    sdk_content = fx_dj_get_dependencies(interfaces[target_interface], root_file, prepr_cmd_line)
    with open(args.sdk, 'w+') as sdk_f:
        for i in sdk_content: sdk_f.write(interfaces[i] + '\n')

print 'Done. Output: %d source files.' % len(output_files)
