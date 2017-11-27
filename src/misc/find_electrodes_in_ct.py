import numpy as np
import nibabel as nib
from sklearn.cluster import FeatureAgglomeration
from sklearn import mixture
import os.path as op
from src.utils import utils
from src.utils import trans_utils as tu
import csv

links_dir = utils.get_links_dir()
SUBJECTS_DIR = utils.get_link_dir(links_dir, 'subjects', 'SUBJECTS_DIR')
MMVT_DIR = utils.get_link_dir(links_dir, 'mmvt')


# ward = FeatureAgglomeration(n_clusters=1000, linkage='ward')
# ward.fit(ct_data)
# print(ward)


def find_nearest_electrde_in_ct(ct_data, x, y, z, max_iters=100):
    from itertools import product
    peak_found, iter_num = True, 0
    while peak_found and iter_num < max_iters:
        max_ct_data = ct_data[x, y, z]
        max_diffs = (0, 0, 0)
        for dx, dy, dz in product([-1, 0, 1], [-1, 0, 1], [-1, 0, 1]):
            print(x+dx, y+dy, z+dz, ct_data[x+dx, y+dy, z+dz], max_ct_data)
            if ct_data[x+dx, y+dy, z+dz] > max_ct_data:
                max_ct_data = ct_data[x+dx, y+dy, z+dz]
                max_diffs = (dx, dy, dz)
        peak_found = max_diffs == (0, 0, 0)
        if not peak_found:
            x, y, z = x+max_diffs[0], y+max_diffs[1], z+max_diffs[2]
            print(max_ct_data, x, y, z)
        iter_num += 1
    if not peak_found:
        print('Peak was not found!')
    print(iter_num, max_ct_data, x, y, z)


def write_freeview_points(centroids):
    fol = op.join(MMVT_DIR, subject, 'freeview')
    utils.make_dir(fol)

    with open(op.join(fol, 'electrodes.dat'), 'w') as fp:
        writer = csv.writer(fp, delimiter=' ')
        writer.writerows(centroids)
        writer.writerow(['info'])
        writer.writerow(['numpoints', len(centroids)])
        writer.writerow(['useRealRAS', '0'])


def clustering(data, ct_data, n_components, n_items_to_remove=0, covariance_type='full'):
    from collections import Counter
    cv_types = ['spherical', 'tied', 'diag', 'full']
    gmm = mixture.GaussianMixture(n_components=n_components, covariance_type=covariance_type)
    gmm.fit(data)
    # print(gmm)
    Y = gmm.predict(data)
    # utils.plot_3d_scatter(data, Y)
    # plot_3d(gmm, data, Y)
    # if n_items_to_remove > 0:
    #     tuples_to_remove = sorted([(v, k) for k, v in Counter(Y).items()])[:n_items_to_remove]
    #     labels_to_remove = [v for v, k in tuples_to_remove]
    #     items_to_remove = np.concatenate((data[Y==label] for label in labels_to_remove))
    #     print('sdff')
    centroids = np.zeros(gmm.means_.shape)
    for ind, label in enumerate(np.unique(Y)):
        voxels = data[Y==label]
        centroids[ind] = voxels[np.argmax([ct_data[tuple(voxel)] for voxel in voxels])]
    # utils.plot_3d_scatter(centroids, [len(data[Y==label]) for label in np.unique(Y)])
    return centroids


def plot_3d(clf, X, Y_):
    import itertools
    import matplotlib.pyplot as plt
    import matplotlib as mpl

    fig, splot = plt.subplots(1,1)
    color_iter = itertools.cycle(['navy', 'turquoise', 'cornflowerblue',
                                  'darkorange'])
    for i, (mean, cov, color) in enumerate(zip(clf.means_, clf.covariances_,
                                               color_iter)):
        v, w = np.linalg.eigh(cov)
        if not np.any(Y_ == i):
            continue
        plt.scatter(X[Y_ == i, 0], X[Y_ == i, 1], .8, color=color)

        # Plot an ellipse to show the Gaussian component
        angle = np.arctan2(w[0][1], w[0][0])
        angle = 180. * angle / np.pi  # convert to degrees
        v = 2. * np.sqrt(2.) * np.sqrt(v)
        ell = mpl.patches.Ellipse(mean, v[0], v[1], 180. + angle, color=color)
        ell.set_clip_box(splot.bbox)
        ell.set_alpha(.5)
        splot.add_artist(ell)
    plt.show()


def mask_ct(voxels, ct_header, brain):
    brain_header = brain.get_header()
    brain_mask = brain.get_data()
    ct_vox2ras, ras2t1_vox, _ = get_trans(ct_header, brain_header)
    ct_ras = tu.apply_trans(ct_vox2ras, voxels)
    t1_vox = tu.apply_trans(ras2t1_vox, ct_ras).astype(int)
    # voxels = voxels[np.where(brain_mask[t1_vox] > 0)]
    voxels = np.array([v for v, t1_v in zip(voxels, t1_vox) if brain_mask[tuple(t1_v)] > 0])
    return voxels


def get_trans(ct_header, brain_header):
    ct_vox2ras = ct_header.get_vox2ras()
    ras2t1_vox = np.linalg.inv(brain_header.get_vox2ras())
    vox2t1_ras_tkr = brain_header.get_vox2ras_tkr()
    return ct_vox2ras, ras2t1_vox, vox2t1_ras_tkr


@utils.check_for_freesurfer
def run_freeview():
    utils.run_script('freeview -v T1.mgz:opacity=0.3 ct.mgz brain.mgz -c electrodes.dat')


def export_electrodes(subject, centroids_t1_ras_tkr):
    import csv
    fol = utils.make_dir(op.join(MMVT_DIR, subject, 'electrodes'))
    csv_fname = op.join(fol, '{}_RAS.csv'.format(subject))
    with open(csv_fname, 'w') as csv_file:
        wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        wr.writerow(['Electrode Name','R','A','S'])
        for ind, elc_pos in enumerate(centroids_t1_ras_tkr):
            wr.writerow(['UN{}'.format(ind), *['{:.2f}'.format(loc) for loc in elc_pos]])


def main(ct_fname, brain_mask_fname, n_components, n_groups, threshold=2000):
    ct = nib.load(ct_fname)
    ct_header = ct.get_header()
    ct_data = ct.get_data()
    brain = nib.load(brain_mask_fname)
    brain_header = brain.get_header()
    ct_vox2ras, ras2t1_vox, vox2t1_ras_tkr = get_trans(ct_header, brain_header)

    voxels = np.where(ct_data > threshold)
    voxels = np.array(voxels).T
    voxels = mask_ct(voxels, ct_header, brain)
    # utils.plot_3d_scatter(voxels)
    # groups = clustering(voxels, ct_data, n_groups+2, 0, 'spherical')
    centroids = clustering(voxels, ct_data, n_components, 0)
    centroids_ras = tu.apply_trans(ct_vox2ras, centroids)
    centroids_t1_vox = tu.apply_trans(ras2t1_vox, centroids_ras).astype(int)
    centroids_t1_ras_tkr = tu.apply_trans(vox2t1_ras_tkr, centroids_t1_vox)
    write_freeview_points(centroids_t1_ras_tkr)
    export_electrodes(subject, centroids_t1_ras_tkr)
    # run_freeview()


if __name__ == '__main__':
    subject = 'nmr01183'
    ct_fname = '/home/npeled/mmvt/nmr01183/freeview/ct.mgz'
    brain_mask_fname = '/home/npeled/mmvt/nmr01183/freeview/brain.mgz'

    import os
    os.chdir(op.join(MMVT_DIR, subject, 'freeview'))
    main(ct_fname, brain_mask_fname, n_components=52, n_groups=6, threshold=2000)