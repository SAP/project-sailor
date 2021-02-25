"""Utility functions useful for all parts of sailor."""

from io import BytesIO

from matplotlib import pyplot as plt
import plotnine as p9


def _p9_to_svg(plotnine_plot):
    """Convert a plotnine plot to an svg string (for inclusion in html output)."""
    matplotlib_plot = plotnine_plot.draw()
    buffer = BytesIO()
    matplotlib_plot.savefig(buffer, format='svg', bbox_inches='tight')
    plt.close(matplotlib_plot)
    return buffer.getvalue().decode()


def _default_plot_theme():
    """Provide a default plot theme for out plots."""
    return p9.theme(axis_text_x=p9.element_text(rotation=45, ha='right'),
                    axis_title_x=p9.element_text(margin={'t': 20}),
                    axis_title_y=p9.element_text(margin={'r': 20}),
                    strip_text_y=p9.element_text(size=7, margin={'l': 5, 'r': 7}),
                    strip_margin=0.05,
                    panel_spacing_y=0.2,
                    )
