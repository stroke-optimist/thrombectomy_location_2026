import pandas as pd
import matplotlib.pyplot as plt
import contextily as ctx  # map tiles


def plot_map(ax, data, **kwargs):
    """
    Plot a choropleth and its colorbar.

    vmin / vmax set the colour scale limits. Leave either as None to set
    it automatically from the data.
    """
    data.plot(ax=ax, **kwargs)

    
def get_hospital(hospitals_gdf, postcode):
    """Return the first matching hospital, or None if it is unavailable."""
    matches = hospitals_gdf.loc[hospitals_gdf["Postcode"].eq(postcode)]
    return None if matches.empty else matches.iloc[0]

    
def draw_arrow(ax, hospitals_gdf, start_postcode, end_postcode):
    """Draw an arrow only when both hospital locations are available."""
    start = get_hospital(hospitals_gdf, start_postcode)
    end = get_hospital(hospitals_gdf, end_postcode)

    if start is None or end is None:
        return

    ax.annotate(
        "",
        xy=(end.geometry.x, end.geometry.y),
        xytext=(start.geometry.x, start.geometry.y),
        arrowprops={
            "arrowstyle": "simple, head_width=0.7, head_length=0.7",
            "facecolor": "white",
            "lw": 0.7,
            "mutation_scale": 15,
        },
        zorder=3,
    )

    
def plot_hospitals(ax, hospitals_gdf, show_new_mt=False, show_labels=True):
    """Plot hospital markers and labels."""
    ivt_mask = pd.to_numeric(
        hospitals_gdf["Use_IVT"], errors="coerce"
    ).eq(1)
    mt_mask = pd.to_numeric(
        hospitals_gdf["Use_MT"], errors="coerce"
    ).eq(1)
    new_mt_mask = pd.to_numeric(
        hospitals_gdf["extra_MT_unit"], errors="coerce"
    ).eq(1)

    hospitals_gdf.loc[ivt_mask].plot(
        ax=ax,
        edgecolor="k",
        facecolor="w",
        markersize=30,
        marker="o",
        zorder=99,
    )
    hospitals_gdf.loc[mt_mask].plot(
        ax=ax,
        edgecolor="k",
        facecolor="w",
        markersize=200,
        marker="*",
        zorder=99,
    )

    if show_new_mt:
        hospitals_gdf.loc[new_mt_mask].plot(
            ax=ax,
            edgecolor="k",
            facecolor="r",
            markersize=300,
            marker="*",
            zorder=99,
        )

    if show_labels:
        ivt_only_mask = ivt_mask & ~mt_mask
        if show_new_mt:
            ivt_only_mask &= ~new_mt_mask
    
        label_groups = [
            (ivt_only_mask, 10, "black"),
            (mt_mask, 12, "red"),
        ]
        if show_new_mt:
            label_groups.append((new_mt_mask, 12, "red"))
    
        for mask, fontsize, color in label_groups:
            for _, hospital in hospitals_gdf.loc[mask].iterrows():
                if hospital["Hospital_City"] in ['Coventry']:
                    label_offset = (8, -5)
                elif hospital["Hospital_City"] in ['Worcester']:
                    label_offset = (5, -3)
                elif hospital["Hospital_City"] in ['Birmingham']:
                    label_offset = (5, 10)
                # elif hospital["Hospital_City"] in ['Southampton']:
                #     label_offset = (-48, 5)
                elif hospital["Hospital_City"] in ['Hereford']:
                    label_offset = (-48, 5)
                elif hospital["Hospital_City"] in ['Barnstaple']:
                    label_offset = (-48, 5)
                elif hospital["Hospital_City"] in ['Dorchester']:
                    label_offset = (5, -5)
                else:
                    label_offset = (5, 5)
                    
                ax.annotate(
                    hospital["Hospital_City"],
                    xy=(hospital.geometry.x, hospital.geometry.y),
                    xytext=label_offset,
                    textcoords="offset points",
                    fontsize=fontsize,
                    color=color,
                    zorder=100,
                    bbox={
                        "facecolor": "white",
                        "edgecolor": "none",
                        "alpha": 0.8,
                        "pad": 1,
                    },
                )
    else:
        pass

    
def add_basemap(ax):
    ctx.add_basemap(
        ax,
        source="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        crs="EPSG:27700",
        zoom="auto",
        alpha=0.25,
        zorder=1,
    )

    
def get_bounds(comparison, hospitals_gdf, used_hospitals):
    """
    
    Define a function to choose sensible axis limits that focus
    on the area around Taunton and Worcester and include all
    affected LSOA and hospitals:
    """
    # Get limits of geometry for plotting
    bounds = comparison.geometry.bounds
    min_lng = bounds['minx'].min()
    max_lng = bounds['maxx'].max()
    min_lat = bounds['miny'].min()
    max_lat = bounds['maxy'].max()
    
    # Include the locations of all base and comparator MT hospitals
    hospital_points = hospitals_gdf.loc[
        hospitals_gdf['Postcode'].isin(used_hospitals), 'geometry'
    ]
    hospital_lngs = hospital_points.x
    hospital_lats = hospital_points.y
    
    min_lng = min(min_lng, hospital_lngs.min())
    max_lng = max(max_lng, hospital_lngs.max())
    min_lat = min(min_lat, hospital_lats.min())
    max_lat = max(max_lat, hospital_lats.max())
    
    # Add a small buffer to the limits for better visualization
    buffer = 10000  # metres
    min_lng -= buffer
    max_lng += buffer# * 4
    min_lat -= buffer
    max_lat += buffer
    return min_lng, min_lat, max_lng, max_lat
