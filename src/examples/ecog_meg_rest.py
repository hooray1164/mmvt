import os.path as op
import glob
import numpy as np
import scipy.interpolate
import matplotlib.pyplot as plt
import shutil
import warnings
import time

from src.utils import utils
from src.preproc import meg as meg
from src.preproc import electrodes
from src.utils import labels_utils as lu

LINKS_DIR = utils.get_links_dir()
SUBJECTS_DIR = utils.get_link_dir(LINKS_DIR, 'subjects', 'SUBJECTS_DIR')
MMVT_DIR = utils.get_link_dir(LINKS_DIR, 'mmvt')
MEG_DIR = utils.get_link_dir(LINKS_DIR, 'meg')


def create_electrodes_labels(subject, bipolar=False, labels_fol_name='electrodes_labels',
        label_r=5, snap=False, sigma=1, overwrite=False, n_jobs=-1):
    electrodes_names, pos = [], []
    electrodes_snap_coordinates_temp = op.join(SUBJECTS_DIR, subject, 'electrodes', '*_snap_electrodes.npz')
    electrodes_snap_coordinates_files = glob.glob(electrodes_snap_coordinates_temp)
    if len(electrodes_snap_coordinates_files) == 0:
        raise Exception('No electrodes snap coordinates files ({})!'.format(electrodes_snap_coordinates_temp))
    for elcs_group_fname in electrodes_snap_coordinates_files:
        d = utils.Bag(np.load(elcs_group_fname))
        group_name = utils.namebase(elcs_group_fname).split('_')[0]
        electrodes_names.extend([
            '{}{}'.format(group_name, str(k + 1).zfill(2)) for k in range(d.snapped_electrodes.shape[0])])
        pos.append(d.snapped_electrodes)
    pos = np.vstack(pos)
    electrodes.create_labels_around_electrodes(
        subject, bipolar, labels_fol_name, label_r, snap, sigma, overwrite=overwrite,
        names=electrodes_names, pos=pos, n_jobs=n_jobs)
    return electrodes.create_labels_around_electrodes(
        subject, bipolar, labels_fol_name, label_r, snap, sigma, overwrite, n_jobs)


def create_atlas_coloring(subject, labels_fol_name='electrodes_labels', n_jobs=-1):
    return lu.create_atlas_coloring(subject, labels_fol_name, n_jobs)


def meg_remove_artifcats(subject, raw_fname):
    meg_args = meg.read_cmd_args(dict(
        subject=subject, mri_subject=subject,
        function='remove_artifacts',
        raw_fname=raw_fname,
        overwrite_ica=True
    ))
    return meg.call_main(meg_args)


def meg_calc_labels_ts(subject, inv_method='MNE', em='mean_flip', atlas='electrodes_labels', remote_subject_dir='',
                       meg_remote_dir='', meg_epochs_dir='', empty_fname='', cor_fname='', use_demi_events=True, n_jobs=-1):
    functions = 'make_forward_solution,calc_inverse_operator,calc_stc,calc_labels_avg_per_condition'

    epochs_files = glob.glob(op.join(
        meg_epochs_dir, '**', '{}_*_Resting_eeg_meg_Demi_ar-epo.fif'.format(subject)))
    output_files = glob.glob(op.join(
        MMVT_DIR, subject, 'meg', 'labels_data_rest_electrodes_labels_dSPM_mean_flip_*.npz'))
    for output_fname in output_files:
        utils.remove_file(output_fname)

    for ind, epo_fname in enumerate(epochs_files):
        # Remove  '/autofs/space/karima_002/users/Machine_Learning_Clinical_MEG_EEG_Resting/epochs/nmr00479_4994627_vef',
        fol = utils.make_dir(op.join(MMVT_DIR, subject, 'meg', utils.namebase(epo_fname)))
        overwrite_source_bem = args.overwrite_source_bem if ind == 0 else False

        meg_args = meg.read_cmd_args(dict(
            subject=subject, mri_subject=subject,
            task='rest', inverse_method=inv_method, extract_mode=em, atlas=atlas,
            single_trial_stc=True,
            recreate_src_spacing='ico5',
            fwd_recreate_source_space=overwrite_source_bem,
            recreate_bem_solution=overwrite_source_bem,
            remote_subject_meg_dir=meg_remote_dir,
            remote_subject_dir=remote_subject_dir,
            epo_fname=epo_fname,
            empty_fname=empty_fname,
            cor_fname=cor_fname,
            function=functions,
            use_demi_events=use_demi_events,
            stc_template=utils.namebase(epo_fname)[:-4],
            # windows_length=10000,
            # windows_shift=5000,
            # overwrite_fwd=True,
            # overwrite_inv=True,
            # overwrite_labels_data=True,
            using_auto_reject=False,
            use_empty_room_for_noise_cov=True,
            read_only_from_annot=False,
            n_jobs=n_jobs
        ))
        meg.call_main(meg_args)

        output_files = glob.glob(op.join(
            MMVT_DIR, subject, 'meg', 'labels_data_rest_electrodes_labels_dSPM_mean_flip_*.npz'))
        for output_fname in output_files:
            utils.move_file(output_fname, fol, overwrite=True)


def meg_preproc(subject, inv_method='MNE', em='mean_flip', atlas='electrodes_labels', remote_subject_dir='',
                meg_remote_dir='', empty_fname='', cor_fname='', use_demi_events=True, calc_labels_avg=False,
                overwrite=False, n_jobs=-1):
    functions = 'calc_epochs,calc_evokes,make_forward_solution,calc_inverse_operator'
    if calc_labels_avg:
        functions += ',calc_stc,calc_labels_avg_per_condition'
    meg_args = meg.read_cmd_args(dict(
        subject=subject, mri_subject=subject,
        task='rest', inverse_method=inv_method, extract_mode=em, atlas=atlas,
        remote_subject_meg_dir=meg_remote_dir,
        remote_subject_dir=remote_subject_dir,
        empty_fname=empty_fname,
        cor_fname=cor_fname,
        function=functions,
        use_demi_events=use_demi_events,
        windows_length=10000,
        windows_shift=5000,
        # power_line_notch_widths=5,
        using_auto_reject=False,
        # reject=False,
        use_empty_room_for_noise_cov=True,
        read_only_from_annot=False,
        overwrite_epochs=overwrite,
        overwrite_evoked=overwrite,
        n_jobs=n_jobs
    ))
    return meg.call_main(meg_args)


def calc_meg_power_spectrum(subject, atlas, inv_method, em, overwrite=False, n_jobs=-1):
    meg_args = meg.read_cmd_args(dict(
        subject=subject, mri_subject=subject,
        task='rest', inverse_method=inv_method, extract_mode=em, atlas=atlas,
        function='calc_source_power_spectrum',
        pick_ori='normal',  # very important for calculation of the power spectrum
        # max_epochs_num=20,
        overwrite_labels_power_spectrum=overwrite,
        n_jobs=n_jobs
    ))
    return meg.call_main(meg_args)


def calc_electrodes_power_spectrum(subject, edf_name, overwrite=False):
    elecs_args = electrodes.read_cmd_args(utils.Bag(
        subject=subject,
        function='create_raw_data_from_edf,calc_epochs_power_spectrum',
        task='rest',
        bipolar=False,
        remove_power_line_noise=True,
        raw_fname='{}.edf'.format(edf_name),
        normalize_data=False,
        preload=True,
        windows_length=10, # s
        windows_shift=5,
        # epochs_num=20,
        overwrite_power_spectrum=overwrite
    ))
    electrodes.call_main(elecs_args)


def filter_meg_labels_ts(subject, inv_method='dSPM', em='mean_flip', atlas='electrodes_labels', low_freq_cut_off=10,
                         fs=1000, do_plot=False, n_jobs=4):
    folders = glob.glob(op.join(MMVT_DIR, subject, 'meg', '{}_*_*_Resting_eeg_meg_Demi_ar-epo'.format(subject)))
    now = time.time()
    for fol_ind, fol in enumerate(folders):
        utils.time_to_go(now, fol_ind, len(folders), runs_num_to_print=1)
        files = glob.glob(op.join(fol, 'labels_data_rest_{}_{}_{}_?h.npz'.format(atlas, inv_method, em)))
        for fname in files:
            hemi = lu.get_hemi_from_name(utils.namebase(fname))
            d = utils.Bag(np.load(fname))
            L = d.data.shape[0] # labels * time * epochs
            filter_data = np.empty(d.data.shape)
            params = [(d.data[label_ind], label_ind, fs,  low_freq_cut_off, do_plot) for label_ind in range(L)]
            results = utils.run_parallel(_filter_meg_label_ts_parallel, params, n_jobs)
            for filter_label_data, label_ind in results:
                filter_data[label_ind] = filter_label_data
            new_fname = op.join(fol, 'labels_data_rest_{}_{}_{}_filter_{}.npz'.format(atlas, inv_method, em, hemi))
            np.savez(new_fname, data=filter_data, names=d.names, conditions=d.conditions)


def _filter_meg_label_ts_parallel(p):
    from mne.filter import high_pass_filter
    label_data, label_ind, fs,  low_freq_cut_off, do_plot = p
    filter_label_data = np.empty(label_data.shape)
    E = label_data.shape[1]
    for epoch_ind in range(E):
        x = label_data[:, epoch_ind]
        if do_plot:
            plt.psd(x, Fs=fs)
            plt.show()
        x_filter = high_pass_filter(x, Fs=fs, Fp=low_freq_cut_off, n_jobs=1, verbose=False)
        if do_plot:
            plt.psd(x_filter, Fs=fs)
            plt.show()
        filter_label_data[:, epoch_ind] = x_filter
    return filter_label_data, label_ind


def combine_meg_and_electrodes_power_spectrum(subject, inv_method='MNE', em='mean_flip', low_freq=None, high_freq=None,
                                              do_plot=True, overwrite=False):
    # https://martinos.org/mne/dev/generated/mne.time_frequency.psd_array_welch.html
    output_fname = op.join(MMVT_DIR, subject, 'electrodes', 'electrodes_data_power_spectrum_comparison.npz')
    # if op.isfile(output_fname) and not overwrite:
    #     return True

    meg_ps_dict = utils.Bag(
        np.load(op.join(MMVT_DIR, subject, 'meg', 'rest_{}_{}_power_spectrum.npz'.format(inv_method, em))))
    elecs_ps_dict = utils.Bag(
        np.load(op.join(MMVT_DIR, subject, 'electrodes', 'power_spectrum.npz'.format(inv_method, em))))

    # Power Spectral Density (dB)
    meg_ps = 10 * np.log10(meg_ps_dict.power_spectrum.squeeze())
    mask = np.where(meg_ps_dict.frequencies > 8)[0]
    np.argmax(np.sum(meg_ps[:, :, mask], axis=(1, 2)))

    plot_power_spectrum(meg_ps, meg_ps_dict.frequencies, 'MEG')
    meg_ps = meg_ps.mean(axis=0)
    elecs_ps = 10 * np.log10(elecs_ps_dict.power_spectrum.squeeze())
    plot_power_spectrum(elecs_ps, elecs_ps_dict.frequencies, 'electrodes')
    elecs_ps = elecs_ps.mean(axis=0)
    meg_func = scipy.interpolate.interp1d(meg_ps_dict.frequencies, meg_ps)
    elecs_func = scipy.interpolate.interp1d(elecs_ps_dict.frequencies, elecs_ps)

    low_freq = int(max([min(meg_ps_dict.frequencies), min(elecs_ps_dict.frequencies), low_freq]))
    high_freq = int(min([max(meg_ps_dict.frequencies), max(elecs_ps_dict.frequencies), high_freq]))
    freqs_num = high_freq - low_freq + 1
    frequencies = np.linspace(low_freq, high_freq, num=freqs_num * 10, endpoint=True)

    meg_ps_inter = meg_func(frequencies)
    meg_ps_inter = (meg_ps_inter - np.mean(meg_ps_inter)) / np.std(meg_ps_inter)
    elecs_ps_inter = elecs_func(frequencies)
    elecs_ps_inter = (elecs_ps_inter - np.mean(elecs_ps_inter)) / np.std(elecs_ps_inter)

    plot_all_results(meg_ps_inter, elecs_ps_inter, frequencies)

    electrodes_meta_fname = op.join(MMVT_DIR, subject, 'electrodes', 'electrodes_meta_data.npz')
    elecs_dict = utils.Bag(np.load(electrodes_meta_fname))
    labels = elecs_dict.names

    data = np.zeros((len(labels), len(frequencies), 2))
    data[:, :, 0] = elecs_ps_inter
    data[:, :, 1] = meg_ps_inter
    np.savez(output_fname, data=data, names=labels, conditions=['grid_rest', 'meg_rest'])

    if do_plot:
        plot_results(meg_ps_dict, elecs_ps_dict, frequencies, meg_ps, meg_ps_inter, elecs_ps, elecs_ps_inter)


def plot_power_spectrum(psds, freqs, title):
    f, ax = plt.subplots()
    psds_mean = psds.mean(0)
    psds_std = psds.std(0)
    for ps_mean, ps_std in zip(psds_mean, psds_std):
        ax.plot(freqs, ps_mean, color='k')
        ax.fill_between(freqs, ps_mean - ps_std, ps_mean + ps_std, color='k', alpha=.5)
    ax.set(title='{} Multitaper PSD'.format(title), xlabel='Frequency',
           ylabel='Power Spectral Density (dB)')
    plt.show()


def plot_all_results(meg_ps_inter, elecs_ps_inter, frequencies):
    fig, ax = plt.subplots(nrows=8, ncols=8, sharex='col', sharey='row')
    ind = 0
    for row in ax:
        for col in row:
            col.plot(frequencies, meg_ps_inter[ind], 'b')
            col.plot(frequencies, elecs_ps_inter[ind], 'r')
            col.set_xlim([0, 60])
            ind += 1
    plt.show()


def plot_results(meg_ps_dict, elecs_ps_dict, frequencies, meg_ps, meg_ps_inter, elecs_ps, elecs_ps_inter):
    plt.figure()
    plt.plot(meg_ps_dict.frequencies, meg_ps.T)
    plt.title('Original MEG PS')
    plt.figure()
    plt.plot(frequencies, meg_ps_inter.T)
    plt.title('Interpolate MEG PS')
    plt.figure()
    plt.plot(elecs_ps_dict.frequencies, elecs_ps.T)
    plt.title('Original Electrodes PS')
    plt.figure()
    plt.plot(frequencies, elecs_ps_inter.T)
    plt.title('Interpolate Electrodes PS')
    plt.show()


def compare_ps_from_epochs_and_from_time_series(subject):
    ps1 = np.load(op.join(MMVT_DIR, subject, 'meg', 'rest_dSPM_mean_flip_power_spectrum_from_epochs.npz'))['power_spectrum'].mean(axis=0).squeeze()
    ps2 = 10 * np.log10(np.load(op.join(MMVT_DIR, subject, 'meg', 'rest_dSPM_mean_flip_power_spectrum.npz'))['power_spectrum'].mean(axis=0).squeeze())
    plt.figure()
    plt.plot(ps1.T)
    plt.title('power spectrum from epochs')
    plt.xlim([0, 100])
    plt.figure()
    plt.plot(ps2.T)
    plt.title('power spectrum from time series')
    plt.xlim([0, 100])
    plt.show()


def check_mmvt_files(subject):
    input_files = glob.glob(op.join(MMVT_DIR, subject, 'meg', '**', 'labels_data_rest_electrodes_labels_dSPM_mean_flip_lh.npz'))
    if len(input_files) < 2:
        print('No enough files!')
        return
    x1 = np.load(input_files[0])['data']
    x2 = np.load(input_files[1])['data']
    if np.array_equal(x1, x2):
        raise Exception('!!! labels are equal !!!')
    print(x1.shape, x2.shape)
    print('OK!')


def check_epochs(subject, meg_epochs_dir):
    import mne
    epochs_files = glob.glob(op.join(
        meg_epochs_dir, '**', '{}_*_Resting_eeg_meg_Demi_ar-epo.fif'.format(subject)))
    if len(epochs_files) < 2:
        print('No enough epochs!')
    ep1 = mne.read_epochs(epochs_files[0])
    ep2 = mne.read_epochs(epochs_files[1])
    if np.array_equal(ep1._data, ep2._data):
        raise Exception('!!! epochs data are equall !!!')
    print('OK!')


def check_meg(subject):
    from src.mmvt_addon import colors_utils as cu

    fol = op.join(MMVT_DIR, subject, 'meg')
    fnames = glob.glob(op.join(fol, '**', 'labels_data_rest_electrodes_labels_dSPM_mean_flip_lh.npz'))
    colors = cu.get_distinct_colors(len(fnames))
    for fname, color in zip(fnames, colors):
        x = np.load(fname)['data']
        plt.plot(x[0, :, 0], color=color)
        del x
    plt.show()


def main(args):
    import os
    seder_root = os.environ.get('SEDER_SUBJECT_META', '')
    if seder_root != '':
        remote_subject_dir = glob.glob(op.join(seder_root, args.subject, 'freesurfer', '*'))[0]
    else:
        remote_subject_dirs = [d for d in [
            '/autofs/space/megraid_clinical/MEG-MRI/seder/freesurfer/{}'.format(args.subject),
            # '/home/npeled/subjects/{}'.format(args.subject),
            op.join(SUBJECTS_DIR, args.subject)] if op.isdir(d)]
        remote_subject_dir = remote_subject_dirs[0] if len(remote_subject_dirs) > 0 else ''
    meg_epochs_dirs = [d for d in [
        '/autofs/space/karima_002/users/Machine_Learning_Clinical_MEG_EEG_Resting/epochs/{}'.format(args.subject),
        # '/home/npeled/meg/{}'.format(args.subject),
        op.join(MEG_DIR, args.subject)] if op.isdir(d)]
    meg_epochs_dir = meg_epochs_dirs[0] if len(meg_epochs_dirs) > 0 else ''
    meg_remote_dirs = [d for d in [
        '/autofs/space/megraid_clinical/MEG/epilepsy/subj_6213848/171127',
        '/home/npeled/meg/{}'.format(args.subject),
        op.join(MEG_DIR, args.subject)] if op.isdir(d)]
    meg_remote_dir = meg_remote_dirs[0] if len(meg_remote_dirs) > 0 else ''
    session_num = 1
    # raw_fnames = glob.glob(op.join(meg_remote_dir, '*_??_raw.fif'))
    raw_fname =  '' #utils.select_one_file(raw_fnames) # raw_fnames[0] if len(raw_fnames) > 0 else ''
    cor_fname = '' #op.join(remote_subject_dir, 'mri', 'T1-neuromag', 'sets', 'COR-naoro-171130.fif') # Can be found automatically
    empty_fname = op.join(meg_remote_dir, 'empty_room_raw.fif')
    inv_method = 'dSPM' # 'MNE'
    em = 'mean_flip'
    overwrite_meg, overwrite_electrodes_labels = True, True
    overwrite_labels_power_spectrum, overwrite_power_spectrum = True, True
    bipolar = False
    labels_fol_name = atlas = 'electrodes_labels'
    label_r = 5
    snap = True
    sigma = 3
    use_demi_events = True
    calc_labels_avg = True

    edf_name = 'SDohaseIIday2'
    low_freq, high_freq = 1, 100

    mmvt_electrodes_labels = op.join(MMVT_DIR, args.subject, 'labels', labels_fol_name)
    subjects_electrodes_labels = op.join(SUBJECTS_DIR, args.subject, 'label', labels_fol_name)
    if op.isdir(mmvt_electrodes_labels) and not op.isdir(subjects_electrodes_labels):
        utils.create_folder_link(mmvt_electrodes_labels, subjects_electrodes_labels)

    if args.function == 'create_electrodes_labels':
        create_electrodes_labels(
            args.subject, bipolar, labels_fol_name, label_r, snap, sigma, overwrite_electrodes_labels, args.n_jobs)
    elif args.function == 'create_atlas_coloring':
        create_atlas_coloring(args.subject, labels_fol_name, args.n_jobs)
    elif args.function == 'meg_remove_artifcats':
        meg_remove_artifcats(args.subject, raw_fname)
    elif args.function == 'meg_preproc':
        meg_preproc(
            args.subject, inv_method, em, atlas, remote_subject_dir, meg_remote_dir, empty_fname,
            cor_fname, use_demi_events, calc_labels_avg, overwrite_meg, args.n_jobs)
    elif args.function == 'meg_calc_labels_ts':
        meg_calc_labels_ts(
            args.subject, inv_method, em, atlas, remote_subject_dir, meg_remote_dir, meg_epochs_dir, empty_fname,
            cor_fname, use_demi_events, args.n_jobs)
    elif args.function == 'calc_meg_power_spectrum':
        calc_meg_power_spectrum(
            args.subject, atlas, inv_method, em, overwrite_labels_power_spectrum, args.n_jobs)
    elif args.function == 'calc_electrodes_power_spectrum':
        calc_electrodes_power_spectrum(args.subject, edf_name, overwrite_power_spectrum)
    elif args.function == 'combine_meg_and_electrodes_power_spectrum':
        combine_meg_and_electrodes_power_spectrum(args.subject, inv_method, em, low_freq, high_freq)
    elif args.function == 'check_mmvt_files':
        check_mmvt_files(args.subject)
    elif args.function == 'check_epochs':
        check_epochs(args.subject, meg_epochs_dir)
    elif args.function == 'compare_ps_from_epochs_and_from_time_series':
        compare_ps_from_epochs_and_from_time_series(args.subject)
    elif args.function == 'filter_meg_labels_ts':
        filter_meg_labels_ts(args.subject, inv_method, em, atlas)
    elif args.function == 'check_meg':
        check_meg(args.subject)


if __name__ == '__main__':
    import argparse
    from src.utils import args_utils as au
    parser = argparse.ArgumentParser(description='MMVT')
    parser.add_argument('-s', '--subject', help='subject name', required=False, default='nmr00479')
    parser.add_argument('-nmr', '--nmr', help='subject name', required=False, default='4994627')
    parser.add_argument('-f', '--function', help='function name', required=False, default='')
    parser.add_argument('--overwrite_source_bem', required=False, default=0, type=au.is_int)
    parser.add_argument('--n_jobs', help='cpu num', required=False, default=-1)

    args = utils.Bag(au.parse_parser(parser))
    args.n_jobs = utils.get_n_jobs(args.n_jobs)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        main(args)
    print('Done!')