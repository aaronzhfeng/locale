"""Generate publication-quality figures for COLM 2026 paper."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
import numpy as np

# -- Global style ---------------------------------------------------------
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 8,
    'axes.labelsize': 8.5,
    'axes.titlesize': 9,
    'xtick.labelsize': 7.5,
    'ytick.labelsize': 7.5,
    'legend.fontsize': 7,
    'legend.handlelength': 1.2,
    'legend.handletextpad': 0.4,
    'legend.columnspacing': 0.8,
    'figure.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
    'axes.linewidth': 0.45,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'xtick.major.width': 0.4,
    'ytick.major.width': 0.4,
    'xtick.major.pad': 2,
    'ytick.major.pad': 2,
    'axes.grid': False,
    'text.usetex': False,
})

# Palette: muted academic tones (desaturated, print-friendly)
PAL = {
    'blue':   '#3D6FA0',
    'red':    '#C25B56',
    'green':  '#4A8C6F',
    'amber':  '#C4963C',
    'grey':   '#A8A8A8',
    'slate':  '#6B7B8D',
    'text':   '#333333',
    'light':  '#E8E8E8',
}

W = 5.5  # column width in inches


# == Figure 1: Synthetic ER per-seed deltas ===============================
def fig_synthetic():
    seeds  = ['g0', 'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9']
    deltas = [-0.9, 14.7, 25.5, 9.7, -1.3, 8.2, 13.9, 33.5, 7.6, 14.1]
    mean_d = np.mean(deltas)

    fig, ax = plt.subplots(figsize=(W, 2.15))
    x = np.arange(len(seeds))

    # Gradient: map positive deltas through a teal sequential palette
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    teal_cmap = LinearSegmentedColormap.from_list('teal_seq', [
        '#A8D8D8',  # light teal (small gains)
        '#5BA3A3',  # medium teal
        '#2E7D7D',  # rich teal (large gains)
    ])
    norm = Normalize(vmin=0, vmax=35)
    colors = []
    for d in deltas:
        if d < 0:
            colors.append('#C4B8AC')  # warm taupe for losses
        else:
            colors.append(teal_cmap(norm(d)))
    ax.bar(x, deltas, width=0.65, color=colors, linewidth=0, zorder=3)

    # Value labels
    outline = [pe.withStroke(linewidth=2.5, foreground='white')]
    for i, d in enumerate(deltas):
        if d < 0:
            ax.text(i, d - 1.0, f'{d:.1f}', ha='center', va='top',
                    fontsize=6, color='#998877')
        elif d > 18:
            ax.text(i, d - 1.0, f'+{d:.1f}', ha='center', va='top',
                    fontsize=6, color='white', fontweight='bold')
        else:
            ax.text(i, d + 0.6, f'+{d:.1f}', ha='center', va='bottom',
                    fontsize=6, color=PAL['text'], path_effects=outline)

    # Mean line
    ax.axhline(mean_d, color=PAL['red'], lw=0.9, ls=(0, (5, 3)),
               zorder=4, alpha=0.85)
    ax.text(-0.35, 35.5, f'mean +{mean_d:.1f} pp',
            ha='left', va='top', fontsize=6.5, color=PAL['red'],
            style='italic')

    # Zero line
    ax.axhline(0, color='#555555', lw=0.4, zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(seeds, fontsize=7.5)
    ax.set_xlabel('Graph seed')
    ax.set_ylabel(r'F1 delta (pp)')
    ax.set_ylim(-5, 38)
    ax.set_axisbelow(True)
    ax.grid(axis='y', lw=0.3, color=PAL['light'], zorder=0)
    ax.grid(axis='x', visible=False)

    fig.savefig('fig5_synthetic_per_seed.pdf')
    fig.savefig('fig5_synthetic_per_seed.png', dpi=300)
    plt.close(fig)
    print('  [ok] fig5_synthetic_per_seed')


# == Figure 2: NCO false-collider dominance ===============================
def fig_nco():
    labels  = ['500', '1K', '2K', '5K', '10K', '20K', '50K']
    fc      = np.array([101, 138, 151, 200, 234, 54, 46])
    fnc     = np.array([5,   11,  3,   0,   0,   0,  1])
    total   = fc + fnc
    fc_rate = 100 * fc / total

    fig, ax1 = plt.subplots(figsize=(W, 2.15))
    x = np.arange(len(labels))
    bw = 0.52

    ax1.bar(x, fc, bw, color=PAL['red'], alpha=0.55, linewidth=0, zorder=3,
            label='False collider')
    ax1.bar(x, fnc, bw, bottom=fc, color=PAL['blue'], alpha=0.50, linewidth=0,
            zorder=3, label='False non-collider')

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_xlabel(r'Sample size ($n$)')
    ax1.set_ylabel('Number of CI errors')
    ax1.set_ylim(0, 268)
    ax1.yaxis.set_major_locator(mticker.MultipleLocator(50))
    ax1.spines['right'].set_visible(True)
    ax1.spines['right'].set_color(PAL['light'])

    # FC rate on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(x, fc_rate, '-', color=PAL['text'], lw=0.9, zorder=5,
             marker='o', markersize=3, markerfacecolor='white',
             markeredgewidth=0.7, markeredgecolor=PAL['text'], label='FC rate')
    ax2.set_ylabel('FC rate (%)', color=PAL['slate'])
    ax2.set_ylim(88, 104)
    ax2.tick_params(axis='y', colors=PAL['slate'])
    ax2.spines['right'].set_color(PAL['slate'])
    ax2.spines['top'].set_visible(False)

    # Rate annotations (white outline for readability over bars)
    outline = [pe.withStroke(linewidth=3, foreground='white')]
    for i, rate in enumerate(fc_rate):
        ax2.text(x[i], rate + 2.2, f'{rate:.1f}',
                 ha='center', va='bottom', fontsize=6.5, color=PAL['text'],
                 fontweight='medium', path_effects=outline, zorder=6)

    # Legend
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='upper left',
               frameon=True, fancybox=False, framealpha=0.92,
               edgecolor=PAL['light'], borderpad=0.3)

    fig.savefig('fig4_nco_false_colliders.pdf')
    fig.savefig('fig4_nco_false_colliders.png', dpi=300)
    plt.close(fig)
    print('  [ok] fig4_nco_false_colliders')


# == Figure 3: Phase ablation =============================================
def fig_ablation():
    networks = ['Insurance', 'Alarm', 'Sachs', 'Child', 'Asia', 'Hepar2']
    phases = {
        'P1: Ego':       [93.1, 88.3, 70.6, 87.5, 100.0, 75.7],
        '+P2: NCO':      [98.6, 89.6, 70.6, 90.6, 100.0, 79.3],
        '+P3: Recon':    [97.3, 90.7, 76.5, 87.0, 100.0, 80.6],
        '+P4: Safety':   [100.0, 90.7, 76.5, 91.3, 100.0, 83.6],
    }
    colors = [PAL['blue'], PAL['amber'], PAL['green'], PAL['red']]
    alphas = [0.70, 0.65, 0.65, 0.65]

    fig, ax = plt.subplots(figsize=(W, 2.15))
    x = np.arange(len(networks))
    n = len(phases)
    bw = 0.17
    offsets = (np.arange(n) - (n - 1) / 2) * bw

    for j, ((lab, vals), col, al) in enumerate(
            zip(phases.items(), colors, alphas)):
        ax.bar(x + offsets[j], vals, bw, label=lab, color=col, alpha=al,
               linewidth=0, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(networks, fontsize=7.5)
    ax.set_ylabel('Orientation accuracy (%)')
    ax.set_ylim(67, 104)
    ax.set_yticks([70, 80, 90, 100])
    ax.yaxis.set_minor_locator(mticker.MultipleLocator(5))
    ax.grid(axis='y', which='major', lw=0.3, color=PAL['light'], zorder=0)
    ax.grid(axis='y', which='minor', lw=0.2, color=PAL['light'], zorder=0,
            ls=':')
    ax.set_axisbelow(True)

    ax.legend(loc='lower left', ncol=4, frameon=True, fancybox=False,
              framealpha=0.92, edgecolor=PAL['light'], borderpad=0.3)

    fig.savefig('fig_ablation.pdf')
    fig.savefig('fig_ablation.png', dpi=300)
    plt.close(fig)
    print('  [ok] fig_ablation')


# == Figure 4: Multi-baseline comparison (dot plot) =======================
def fig_comparison():
    """Dot plot comparing LOCALE against multiple baselines across networks."""
    # Networks sorted by LOCALE F1 (ascending) for visual impact
    networks = ['Hepar2', 'Water', 'Hailfinder', 'Win95pts',
                'Alarm', 'Insurance', 'Sachs', 'Mildew',
                'Child', 'Asia', 'Cancer']
    nodes    = [70, 32, 56, 76, 37, 27, 11, 35, 20, 8, 5]

    # LOCALE (same model, Table 2)
    locale = [0.565, 0.579, 0.616, 0.694,
              0.841, 0.845, 0.865, 0.859,
              0.882, 0.900, 0.964]
    locale_std = [0.026, 0.068, 0.020, 0.091,
                  0.070, 0.019, 0.044, 0.036,
                  0.030, 0.100, 0.062]

    # MosaCD same model (Qwen3.5-27B, 4096 ctx, Table 2)
    mosacd_same = [0.405, 0.569, 0.449, 0.573,
                   0.801, 0.757, 0.557, 0.859,
                   0.871, 0.967, 0.964]
    mosacd_same_std = [0.029, 0.049, 0.011, 0.057,
                       0.047, 0.083, 0.063, 0.032,
                       0.035, 0.033, 0.062]

    # MosaCD published (GPT-4o-mini, 128K ctx, Table 3)
    mosacd_pub = [0.72, 0.59, 0.49, 0.81,
                  0.93, 0.87, None, 0.90,
                  0.90, 0.93, 1.00]

    # Random baseline: 50% orientation on skeleton edges
    # F1 = 2*p*r/(p+r) where p = skel_recall * 0.5 / (skel_recall * 0.5 + skel_fp * 0.5)
    # Simplification: random orients each skeleton edge with 50% chance correct
    # so TP ~ 0.5 * |skel & GT|, FP ~ 0.5 * |skel & GT| + |skel - GT|
    # Approximate as 0.5 * skeleton_F1 for skeleton-constrained random
    # Using skeleton recalls from paper + assuming ~95% skeleton precision:
    skel_recall = [0.52, 0.50, 0.55, 0.60,
                   0.957, 0.808, 1.00, 0.80,
                   0.96, 1.00, 1.00]
    random_f1 = [r * 0.5 for r in skel_recall]  # ~half correct by chance

    fig, ax = plt.subplots(figsize=(W, 3.0))
    y = np.arange(len(networks))
    dy = 0.22  # vertical offset between methods

    # Plot each method
    # Random
    ax.scatter(random_f1, y + 1.5*dy, marker='x', s=18, color=PAL['grey'],
               linewidths=0.8, zorder=3, label='Random')

    # MosaCD published (hollow diamonds)
    pub_x = [v for v in mosacd_pub if v is not None]
    pub_y = [y[i] + 0.5*dy for i, v in enumerate(mosacd_pub) if v is not None]
    ax.scatter(pub_x, pub_y, marker='D', s=22, facecolors='none',
               edgecolors=PAL['amber'], linewidths=0.9, zorder=4,
               label='MosaCD (GPT-4o-mini)')

    # MosaCD same model (filled squares)
    ax.errorbar(mosacd_same, y - 0.5*dy, xerr=mosacd_same_std,
                fmt='s', markersize=3.5, color=PAL['red'], ecolor=PAL['red'],
                elinewidth=0.5, capsize=1.5, capthick=0.5, alpha=0.75,
                zorder=4, label='MosaCD (Qwen-27B)')

    # LOCALE (filled circles, prominent)
    ax.errorbar(locale, y - 1.5*dy, xerr=locale_std,
                fmt='o', markersize=4, color=PAL['blue'], ecolor=PAL['blue'],
                elinewidth=0.5, capsize=1.5, capthick=0.5,
                zorder=5, label='LOCALE (Qwen-27B)')

    # Network labels with node count
    ylabels = [f'{n} ({v}n)' for n, v in zip(networks, nodes)]
    ax.set_yticks(y)
    ax.set_yticklabels(ylabels, fontsize=7)
    ax.set_xlabel('Directed-edge F1')
    ax.set_xlim(0.15, 1.05)
    ax.invert_yaxis()

    ax.grid(axis='x', lw=0.3, color=PAL['light'], zorder=0)
    ax.grid(axis='y', visible=False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)

    ax.legend(loc='lower right', frameon=True, fancybox=False,
              framealpha=0.92, edgecolor=PAL['light'], borderpad=0.4,
              fontsize=7, handletextpad=0.3)

    fig.savefig('fig_comparison.pdf')
    fig.savefig('fig_comparison.png', dpi=300)
    plt.close(fig)
    print('  [ok] fig_comparison')


# =========================================================================
if __name__ == '__main__':
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print('Generating figures...')
    fig_synthetic()
    fig_nco()
    fig_ablation()
    fig_comparison()
    print('Done.')
