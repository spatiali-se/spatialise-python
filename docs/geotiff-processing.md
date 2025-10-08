# GeoTIFF Processing

This guide explains how to download, process, and visualize soil organic carbon prediction results returned as Cloud-Optimized GeoTIFF (COG) files.

## Overview

Each completed prediction job provides a signed URL to download a Cloud-Optimized GeoTIFF file containing soil organic carbon density predictions for the specified geographic area and year.

### Cloud-Optimized GeoTIFF

COG files are regular GeoTIFF files with internal organization optimized for cloud-based workflows:

- **Tiled structure**: Data organized in tiles for efficient partial reading
- **Overview pyramids**: Multiple resolutions for fast visualization at different zoom levels
- **HTTP range request support**: Read specific portions without downloading entire file

## Downloading Results

### Signed URL Access

Results are accessed via time-limited signed URLs:

```python
from spatialise import SpatialiseSoilPrediction

client = SpatialiseSoilPrediction()
status = client.batch.retrieve_status('batch_abc123')

for job in status.jobs:
    if job.status == 'completed':
        print(f"Job {job.job_id}:")
        print(f"  URL: {job.signed_cog_url}")
        print(f"  Expires: {job.signed_url_expires_at}")
```

Signed URLs typically expire after 24 hours.

### Basic Download

Download GeoTIFF files using `requests`:

```python
import requests
from pathlib import Path

def download_geotiff(url, output_path):
    """Download GeoTIFF from signed URL.

    Parameters
    ----------
    url : str
        Signed COG URL.
    output_path : str or Path
        Output file path.

    Returns
    -------
    Path
        Path to downloaded file.
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path

# Usage
for job in status.jobs:
    if job.status == 'completed':
        output_file = download_geotiff(
            job.signed_cog_url,
            f"results/{job.job_id}.tif"
        )
        print(f"Downloaded: {output_file}")
```

### Concurrent Downloads

Download multiple files in parallel:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from pathlib import Path

def download_batch_results(status, output_dir, max_workers=4):
    """Download all completed job results in parallel.

    Parameters
    ----------
    status : BatchRetrieveStatusResponse
        Batch status containing job results.
    output_dir : str or Path
        Output directory for GeoTIFF files.
    max_workers : int, default=4
        Maximum concurrent downloads.

    Returns
    -------
    list of Path
        Downloaded file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    completed_jobs = [
        job for job in status.jobs
        if job.status == 'completed'
    ]

    def download_job(job):
        output_path = output_dir / f"{job.job_id}.tif"
        response = requests.get(job.signed_cog_url, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path

    downloaded_files = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_job, job): job
            for job in completed_jobs
        }

        for future in as_completed(futures):
            try:
                file_path = future.result()
                downloaded_files.append(file_path)
                print(f"Downloaded: {file_path}")
            except Exception as e:
                job = futures[future]
                print(f"Failed to download {job.job_id}: {e}")

    return downloaded_files
```

### Direct Storage to Cloud

Upload directly to cloud storage without local storage:

```python
import boto3
import requests

def upload_to_s3(signed_url, bucket_name, object_key):
    """Stream GeoTIFF from signed URL to S3.

    Parameters
    ----------
    signed_url : str
        Signed COG URL from API.
    bucket_name : str
        S3 bucket name.
    object_key : str
        S3 object key.

    Returns
    -------
    str
        S3 object URL.
    """
    s3 = boto3.client('s3')

    # Stream download
    response = requests.get(signed_url, stream=True)
    response.raise_for_status()

    # Upload to S3
    s3.upload_fileobj(
        response.raw,
        bucket_name,
        object_key,
        ExtraArgs={'ContentType': 'image/tiff'}
    )

    return f"s3://{bucket_name}/{object_key}"


# Usage
for job in status.jobs:
    if job.status == 'completed':
        s3_url = upload_to_s3(
            job.signed_cog_url,
            bucket_name='my-results-bucket',
            object_key=f'predictions/{job.job_id}.tif'
        )
        print(f"Uploaded to: {s3_url}")
```

## Reading GeoTIFF Data

### Reading with Rasterio

Rasterio provides Pythonic access to geospatial raster data:

```python
import rasterio
import numpy as np

def read_geotiff(file_path):
    """Read GeoTIFF metadata and data.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.

    Returns
    -------
    dict
        Dictionary containing metadata and data array.
    """
    with rasterio.open(file_path) as src:
        # Read metadata
        metadata = {
            'width': src.width,
            'height': src.height,
            'crs': src.crs,
            'bounds': src.bounds,
            'transform': src.transform,
            'nodata': src.nodata,
            'dtype': src.dtypes[0]
        }

        # Read data
        data = src.read(1)  # Read first band

        return {
            'metadata': metadata,
            'data': data
        }

# Usage
result = read_geotiff('results/job_001.tif')
print(f"Shape: {result['data'].shape}")
print(f"CRS: {result['metadata']['crs']}")
print(f"Bounds: {result['metadata']['bounds']}")
```

### Reading Remote COG Files

Read COG files directly from signed URL without downloading:

```python
import rasterio
from rasterio.session import AWSSession

def read_remote_cog(signed_url, window=None):
    """Read COG directly from URL.

    Parameters
    ----------
    signed_url : str
        Signed COG URL.
    window : rasterio.windows.Window, optional
        Spatial window to read.

    Returns
    -------
    numpy.ndarray
        Raster data array.
    """
    # Configure for unsigned URLs
    with rasterio.Env(CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
        with rasterio.open(signed_url) as src:
            if window:
                data = src.read(1, window=window)
            else:
                data = src.read(1)

            return data

# Usage
# Read small window without downloading entire file
from rasterio.windows import Window

window = Window(col_off=0, row_off=0, width=512, height=512)
data = read_remote_cog(job.signed_cog_url, window=window)
```

### Extract Statistics

Compute statistics from raster data:

```python
import rasterio
import numpy as np

def compute_raster_statistics(file_path):
    """Compute comprehensive raster statistics.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.

    Returns
    -------
    dict
        Statistical summary.
    """
    with rasterio.open(file_path) as src:
        data = src.read(1)
        nodata = src.nodata

        # Mask nodata values
        if nodata is not None:
            valid_data = data[data != nodata]
        else:
            valid_data = data.flatten()

        stats = {
            'min': float(np.min(valid_data)),
            'max': float(np.max(valid_data)),
            'mean': float(np.mean(valid_data)),
            'median': float(np.median(valid_data)),
            'std': float(np.std(valid_data)),
            'percentile_25': float(np.percentile(valid_data, 25)),
            'percentile_75': float(np.percentile(valid_data, 75)),
            'valid_pixels': len(valid_data),
            'nodata_pixels': np.sum(data == nodata) if nodata else 0
        }

        return stats

# Usage
stats = compute_raster_statistics('results/job_001.tif')
print(f"Mean SOC: {stats['mean']:.2f}")
print(f"Range: {stats['min']:.2f} - {stats['max']:.2f}")
```

## Data Processing

### Reprojection

Reproject raster to different coordinate system:

```python
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

def reproject_raster(input_path, output_path, dst_crs='EPSG:4326'):
    """Reproject raster to target CRS.

    Parameters
    ----------
    input_path : str
        Input GeoTIFF path.
    output_path : str
        Output GeoTIFF path.
    dst_crs : str, default='EPSG:4326'
        Target coordinate reference system.

    Returns
    -------
    str
        Output file path.
    """
    with rasterio.open(input_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.width,
            src.height,
            *src.bounds
        )

        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )

    return output_path

# Usage
reprojected = reproject_raster(
    'results/job_001.tif',
    'results/job_001_wgs84.tif',
    dst_crs='EPSG:4326'
)
```

### Clipping to Area of Interest

Clip raster to specific geometry:

```python
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping

def clip_raster(input_path, output_path, geometry):
    """Clip raster to geometry.

    Parameters
    ----------
    input_path : str
        Input GeoTIFF path.
    output_path : str
        Output GeoTIFF path.
    geometry : shapely.geometry
        Clipping geometry.

    Returns
    -------
    numpy.ndarray
        Clipped raster data.
    """
    with rasterio.open(input_path) as src:
        # Clip raster
        out_image, out_transform = mask(
            src,
            [mapping(geometry)],
            crop=True
        )

        # Update metadata
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        # Write output
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)

        return out_image[0]

# Usage
from shapely.geometry import box

# Define bounding box
bbox = box(minx=6.7, miny=52.8, maxx=6.75, maxy=52.85)

clipped_data = clip_raster(
    'results/job_001.tif',
    'results/job_001_clipped.tif',
    bbox
)
```

### Resampling

Change raster resolution:

```python
import rasterio
from rasterio.enums import Resampling

def resample_raster(input_path, output_path, scale_factor=0.5):
    """Resample raster to different resolution.

    Parameters
    ----------
    input_path : str
        Input GeoTIFF path.
    output_path : str
        Output GeoTIFF path.
    scale_factor : float, default=0.5
        Scale factor for resolution (< 1 for downsampling, > 1 for upsampling).

    Returns
    -------
    str
        Output file path.
    """
    with rasterio.open(input_path) as src:
        # Calculate new dimensions
        new_width = int(src.width * scale_factor)
        new_height = int(src.height * scale_factor)

        # Read data with resampling
        data = src.read(
            out_shape=(src.count, new_height, new_width),
            resampling=Resampling.bilinear
        )

        # Update transform
        transform = src.transform * src.transform.scale(
            (src.width / new_width),
            (src.height / new_height)
        )

        # Write output
        profile = src.profile.copy()
        profile.update({
            'width': new_width,
            'height': new_height,
            'transform': transform
        })

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(data)

    return output_path

# Usage
downsampled = resample_raster(
    'results/job_001.tif',
    'results/job_001_downsampled.tif',
    scale_factor=0.5  # Half resolution
)
```

## Visualization

### Matplotlib Visualization

Create basic visualization with matplotlib:

```python
import rasterio
import matplotlib.pyplot as plt
import numpy as np

def visualize_raster(file_path, title='Soil Organic Carbon Density'):
    """Visualize raster data with matplotlib.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.
    title : str, default='Soil Organic Carbon Density'
        Plot title.

    Returns
    -------
    matplotlib.figure.Figure
        Generated figure.
    """
    with rasterio.open(file_path) as src:
        data = src.read(1)
        nodata = src.nodata

        # Mask nodata values
        if nodata is not None:
            data = np.ma.masked_equal(data, nodata)

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot raster
        im = ax.imshow(data, cmap='YlOrRd', interpolation='nearest')

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='SOC (g/kg)')

        # Add title and labels
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Pixel X')
        ax.set_ylabel('Pixel Y')

        plt.tight_layout()
        return fig

# Usage
fig = visualize_raster('results/job_001.tif')
fig.savefig('results/job_001_visualization.png', dpi=300, bbox_inches='tight')
plt.close()
```

### Geographic Visualization

Create map with coordinate system:

```python
import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt

def create_georeferenced_plot(file_path, output_path=None):
    """Create georeferenced plot.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.
    output_path : str, optional
        Output path for saving figure.

    Returns
    -------
    matplotlib.figure.Figure
        Generated figure.
    """
    with rasterio.open(file_path) as src:
        fig, ax = plt.subplots(figsize=(12, 10))

        # Plot with geographic coordinates
        show(src, ax=ax, cmap='YlOrRd', title='SOC Density')

        # Add colorbar
        image = ax.get_images()[0]
        cbar = plt.colorbar(image, ax=ax, label='SOC (g/kg)')

        # Add coordinates
        ax.set_xlabel(f'Easting ({src.crs})')
        ax.set_ylabel(f'Northing ({src.crs})')

        plt.tight_layout()

        if output_path:
            fig.savefig(output_path, dpi=300, bbox_inches='tight')

        return fig

# Usage
fig = create_georeferenced_plot(
    'results/job_001.tif',
    'results/job_001_geo.png'
)
```

### Interactive Web Maps

Create interactive Leaflet map:

```python
import rasterio
import folium
from rasterio.warp import calculate_default_transform, reproject

def create_web_map(file_path, output_html='map.html'):
    """Create interactive Leaflet map.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.
    output_html : str, default='map.html'
        Output HTML file path.

    Returns
    -------
    folium.Map
        Folium map object.
    """
    with rasterio.open(file_path) as src:
        # Get bounds
        bounds = src.bounds
        center_lat = (bounds.bottom + bounds.top) / 2
        center_lon = (bounds.left + bounds.right) / 2

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13
        )

        # Add rectangle overlay for bounds
        folium.Rectangle(
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            color='red',
            fill=True,
            fillOpacity=0.1,
            popup=f"Prediction Area<br>File: {file_path}"
        ).add_to(m)

        # Save map
        m.save(output_html)

        return m

# Usage
web_map = create_web_map('results/job_001.tif', 'results/map.html')
```

## Integration Patterns

### PostGIS Integration

Load raster into PostGIS database:

```python
import rasterio
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def load_into_postgis(file_path, table_name, db_params):
    """Load GeoTIFF into PostGIS raster table.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.
    table_name : str
        PostGIS table name.
    db_params : dict
        Database connection parameters.

    Returns
    -------
    str
        Table name.
    """
    # Use raster2pgsql command
    import subprocess

    cmd = [
        'raster2pgsql',
        '-s', '4326',  # SRID
        '-I',  # Create spatial index
        '-C',  # Apply constraints
        '-M',  # Vacuum analyze
        file_path,
        table_name
    ]

    # Execute and pipe to psql
    raster_sql = subprocess.check_output(cmd)

    # Connect to database
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Execute SQL
    cur.execute(raster_sql.decode('utf-8'))

    cur.close()
    conn.close()

    return table_name

# Usage
load_into_postgis(
    'results/job_001.tif',
    'soc_predictions',
    db_params={
        'host': 'localhost',
        'database': 'gis',
        'user': 'postgres',
        'password': 'password'
    }
)
```

### Export to Multiple Formats

Convert GeoTIFF to various formats:

```python
import rasterio
from pathlib import Path

def export_formats(input_path, output_dir):
    """Export raster to multiple formats.

    Parameters
    ----------
    input_path : str
        Input GeoTIFF path.
    output_dir : str
        Output directory.

    Returns
    -------
    dict
        Paths to exported files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(input_path).stem
    outputs = {}

    with rasterio.open(input_path) as src:
        # PNG (8-bit)
        data = src.read(1)
        data_normalized = ((data - data.min()) / (data.max() - data.min()) * 255).astype('uint8')

        png_profile = src.profile.copy()
        png_profile.update(driver='PNG', dtype='uint8', count=1)

        png_path = output_dir / f"{base_name}.png"
        with rasterio.open(png_path, 'w', **png_profile) as dst:
            dst.write(data_normalized, 1)
        outputs['png'] = png_path

        # NetCDF
        nc_profile = src.profile.copy()
        nc_profile.update(driver='netCDF')

        nc_path = output_dir / f"{base_name}.nc"
        with rasterio.open(nc_path, 'w', **nc_profile) as dst:
            dst.write(src.read(1), 1)
        outputs['netcdf'] = nc_path

        # GeoJSON (convert to vector points)
        # This would require additional processing

    return outputs

# Usage
exports = export_formats('results/job_001.tif', 'results/exports/')
print(f"Exported to: {list(exports.values())}")
```

## Performance Optimization

### Parallel Processing

Process multiple GeoTIFFs in parallel:

```python
from concurrent.futures import ProcessPoolExecutor
import rasterio
import numpy as np

def process_single_raster(file_path):
    """Process single raster file.

    Parameters
    ----------
    file_path : str
        Path to GeoTIFF file.

    Returns
    -------
    dict
        Processing results.
    """
    with rasterio.open(file_path) as src:
        data = src.read(1)
        nodata = src.nodata

        valid_data = data[data != nodata] if nodata else data.flatten()

        return {
            'file': file_path,
            'mean': float(np.mean(valid_data)),
            'std': float(np.std(valid_data)),
            'min': float(np.min(valid_data)),
            'max': float(np.max(valid_data))
        }

def process_batch_parallel(file_paths, max_workers=4):
    """Process multiple rasters in parallel.

    Parameters
    ----------
    file_paths : list of str
        List of GeoTIFF file paths.
    max_workers : int, default=4
        Maximum parallel workers.

    Returns
    -------
    list of dict
        Processing results for each file.
    """
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_single_raster, file_paths))

    return results

# Usage
file_list = ['results/job_001.tif', 'results/job_002.tif', 'results/job_003.tif']
results = process_batch_parallel(file_list, max_workers=4)

for result in results:
    print(f"{result['file']}: mean={result['mean']:.2f}")
```

## See Also

- [Webhook Integration](./webhooks.md) - Automate result download
- [Production Patterns](./production-patterns.md) - Cloud storage integration
- [Rasterio Documentation](https://rasterio.readthedocs.io/) - Complete rasterio guide
- [GDAL Documentation](https://gdal.org/) - GDAL/OGR tools
