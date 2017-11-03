#!/usr/bin/env python3
# encoding: utf-8
'''
Ligandum -- Analysis of ligandability mass spectrometry

Created by Matthias Stahl at TU Muenchen, 2017
'''

import ursgal
import pymzml
import pyqms
import pickle
import os
import numpy as np


def showStartHello():
    print('{0:-^100}'.format('###'))
    print('{0:-^100}'.format('This is Ligandum speaking! Let\'s start...'))
    print('{0:-^100}'.format('###'))
    print()
    return


def new_userdefined_unimod_molecule(mass, name, composition):
    # make modification dictionary
    modification_dict = {
        'mass' : mass,
        'name' : name,
        'composition' : composition,
        'id': '1'
    }
    
    # initialize unimod mapper and write to unimod.xml
    u = ursgal.UnimodMapper()
    u.writeXML(modification_dict, xmlFile = '/Library/Frameworks/Python.framework/Versions/3.5/lib/python3.5/site-packages/pyqms/kb/ext/unimod.xml')
    return

    
def msms_identification(mzml_file, database_file):
    # define parameters
    params = {
        'enzyme': 'trypsin',
        'frag_mass_tolerance': 0.5,
        'frag_mass_tolerance_unit': 'da',
        'decoy_generation_mode' : 'reverse_protein',
        'precursor_min_charge' : '2',
        'modifications' : [
            'M,opt,any,Oxidation',
            'C,fix,any,Carbamidomethyl',
            'K,opt,any,TEV_H',
            'K,opt,any,TEV_L'
        ],
    }
    
    # initialize Ursgal controller
    uc = ursgal.UController(
        params = params
    )
    
    # generate reverse protein sequences and initialize new database
    new_target_decoy_db_name = uc.generate_target_decoy(
        input_files = database_file,
        output_file_name = 'new_target_decoy.fasta',
    )
    print('Generated target decoy database: {0}'.format(new_target_decoy_db_name))
    uc.params['database'] = new_target_decoy_db_name
    
    # perform search with search engine (writes output files to file system)
    search_result = uc.search(
        input_file = mzml_file,
        engine = 'msgfplus_v2016_09_16'
    )
    
    # validate search engine results with percolator (writes output files to file system)
    validated_result = uc.validate(
        input_file = search_result,
        engine     = 'percolator_2_08',
    )
    
    filter_params = {
        'csv_filter_rules': [
            ['PEP', 'lte', 0.01],
            ['Is decoy', 'equals', 'false']
        ]
    }
    csv_file_to_filter = '/Users/MS/Desktop/special_projects/SMHacker/msgfplus_v2016_09_16/170209_SMH_170205_P9_05_new_msgfplus_v2016_09_16_pmap_unified_percolator_validated.csv'
    uc = ursgal.UController(
        params = filter_params
    )

    filtered_csv = uc.filter_csv(
        input_file = csv_file_to_filter,
    )
    
    return filtered_csv


def ligandability_quantification(mzml_file, molecule_list, evidence_lookup, formatted_fixed_labels):
    run = pymzml.run.Reader(mzml_file)
    params = {
        'molecules'        : molecule_list,
        'charges'          : [1, 2, 3, 4, 5],
        'fixed_labels'     : formatted_fixed_labels,
        'verbose'          : True,
        'evidences'        : evidence_lookup
    }
    
    lib = pyqms.IsotopologueLibrary( **params )
    
    results = None
    mzml_file_basename = os.path.basename(mzml_file)
    for spectrum in run:
        if spectrum['ms level'] == 1:
            results = lib.match_all(
                mz_i_list = spectrum.centroidedPeaks,
                file_name = mzml_file_basename,
                spec_id   = spectrum['id'],
                spec_rt   = spectrum['scan time'] / 60,
                results   = results
            )
    return results

def edit_molecule_list(molecule_list, evidence_lookup, labels):
    # delete molecules with more than one TEV modification
    for molecule in molecule_list[:]:
        num_of_labels = 0
        for label in labels:
            num_of_labels += molecule.count(label['name'])
        if not num_of_labels == 1:
            molecule_list.remove(molecule)
    print('Initially found {0} peptides via MS2 sequencing. Now I\'ll look for nonsequenced partners.'.format(len(molecule_list)))
    
    # now check for missing partners that were not identified via MS2
    for molecule in molecule_list[:]:
        check_pairs(molecule, molecule_list, evidence_lookup, labels)
    
    print('There are {0} peptides after partner generation.'.format(len(molecule_list)))
    
    return


def check_pairs(molecule, molecule_list, evidence_lookup, labels):
    partner_label_name = ''
    current_label_name = ''
    for label in labels:
        if molecule.count(label['name']) == 0:
            partner_label_name = label['name']
        else:
            current_label_name = label['name']
    
    # generate partner molecule
    partner_molecule = molecule.replace(current_label_name, partner_label_name)
    
    if not partner_molecule in molecule_list:
        # new partner molecule should be added to the molecule list
        molecule_list.append(partner_molecule)
        
        # find molecule in evidence lookup
        c = pyqms.ChemicalComposition()
        c.use(molecule)
        if molecule in evidence_lookup[c.hill_notation_unimod()]:
            trivial_names = evidence_lookup[c.hill_notation_unimod()][molecule]['trivial_names'].copy()
            trivial_names.extend({'no MS2': True})
            evidence = evidence_lookup[c.hill_notation_unimod()][molecule]['evidences'].copy()
            tmp_dict = {
                partner_molecule:
                {
                    'evidences': evidence,
                    'trivial_names': trivial_names
                }
            }
            c.clear()
            c.use(partner_molecule)
            evidence_lookup[c.hill_notation_unimod()] = tmp_dict
        c.clear()
    return


def calculate_ligandability_ratios(results):
    
    return


def main():
    showStartHello()
    
    # add new modifications
    labels = [
        {
            'name': 'TEV_H',
            'mass': '470.26338',
            'composition': {'C': 15, '13C': 5, 'H': 32, 'N': 7, '15N': 1, 'O': 5}
        },
        {
            'name': 'TEV_L',
            'mass': '464.24957',
            'composition': {'C': 20, 'H': 32, 'N': 8, 'O': 5}
        }
    ]
    
    for label in labels:
        new_userdefined_unimod_molecule(label['mass'], label['name'], label['composition'])
    
    # MS/MS identification and validation, output is written to file system
    database_file = '/Users/MS/Desktop/special_projects/SMHacker/28092017human.fasta'
    mzml_file = '/Users/MS/Desktop/special_projects/SMHacker/170209_SMH_170205_P9_05_new.mzML'
    filtered_result = msms_identification(mzml_file, database_file)
    
    # MS isotopic ligandability quantification
    evidence_file = filtered_result
    out_folder = '/Users/MS/Desktop/special_projects/SMHacker/msgfplus_v2016_09_16'

    formatted_fixed_labels, evidence_lookup, molecule_list = pyqms.adaptors.parse_evidence(
        fixed_labels         = None,
        evidence_files       = [ evidence_file ],
        evidence_score_field = 'PEP'
    )

    edit_molecule_list(molecule_list, evidence_lookup, labels)
    
    results = ligandability_quantification(mzml_file, molecule_list, evidence_lookup, formatted_fixed_labels)

    
    # serialize, not really necessary...
    pickle.dump(
        results,
        open(
            '/Users/MS/Desktop/special_projects/SMHacker/pyQms_results.pkl',
            'wb'
        )
    )
    
    # deserialize
    results_class = pickle.load(
        open(
            '/Users/MS/Desktop/special_projects/SMHacker/pyQms_results.pkl',
            'rb'
        )
    )
    rt_border_tolerance = 1

    quant_summary_file  = '/Users/MS/Desktop/special_projects/SMHacker/quant_summary.csv'
    results_class.write_rt_info_file(
        output_file         = quant_summary_file,
        list_of_csvdicts    = None,
        trivial_name_lookup = None,
        rt_border_tolerance = rt_border_tolerance,
        update              = True
    )
    # Todo: does not work with imputed pair peptides...
    results_class.calc_amounts_from_rt_info_file(
        rt_info_file         = quant_summary_file,
        rt_border_tolerance  = rt_border_tolerance,
        calc_amount_function = calc_auc
    )
    
    results.write_result_csv(out_folder + '/ligand_quant_res.csv')
    
    calculate_ligandability_ratios(results)
    return


def calc_auc(obj_for_calc_amount):
    return_dict = None
    if len(obj_for_calc_amount['i']) != 0:
        maxI          = max(obj_for_calc_amount['i'])
        index_of_maxI = obj_for_calc_amount['i'].index(maxI)
        amount_rt     = obj_for_calc_amount['rt'][index_of_maxI]
        amount_score  = obj_for_calc_amount['scores'][index_of_maxI]

        sumI = 0
        for i in obj_for_calc_amount['i']:
            sumI += i
            
        aucI = np.trapz(x = obj_for_calc_amount['rt'], y = obj_for_calc_amount['i'])
        
        return_dict = {
            'max I in window'         : maxI,
            'max I in window (rt)'    : amount_rt,
            'max I in window (score)' : amount_score,
            'sum I in window'         : sumI,
            'auc in window'           : aucI
        }
    return return_dict


if __name__ == '__main__':
    main()
