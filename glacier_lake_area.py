import csv
import sys
import ee
ee.Initialize(project="nepal-glacier-tracker")
import matplotlib.pyplot as plt

PROJECT = "nepal-glacier-tracker"
LAKE_NAME = "Imja Tsho"
AOI = ee.Geometry.Rectangle([86.905, 27.888, 86.945, 27.908])
START_YEAR = 2017
END_YEAR = 2025
NDWI_THRESHOLD = 0.2
MAX_CLOUD_PCT = 40


def mask_s2(image):
    scl = image.select("SCL")
    bad = [0, 1, 3, 8, 9, 10, 11]
    return image.updateMask(scl.remap(bad, [0] * len(bad), 1))


def yearly_water(year):
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterBounds(AOI)
           .filterDate(f"{year}-10-01", f"{year}-11-30")
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PCT))
           .map(mask_s2))
    count = col.size().getInfo()
    if count == 0:
        return None, 0
    ndwi = col.median().clip(AOI).normalizedDifference(["B3", "B8"]).rename("NDWI")
    return ndwi.gt(NDWI_THRESHOLD).selfMask(), count


def water_area_km2(water):
    area = water.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=AOI, scale=10, maxPixels=1e9)
    return (area.get("NDWI").getInfo() or 0) / 1e6


def main():
    ee.Initialize(project=PROJECT)
    rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        water, count = yearly_water(year)
        if water is None:
            print(f"{year}: no images")
            continue
        area = water_area_km2(water)
        rows.append((year, round(area, 3), count))
        print(f"{year}: {area:.3f} km2 ({count} images)")
        print("   mask:", water.getThumbURL({"region": AOI, "dimensions": 400, "palette": ["0066ff"]}))
    with open("imja_tsho_area.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "area_km2", "image_count"])
        w.writerows(rows)
    plt.plot([r[0] for r in rows], [r[1] for r in rows], marker="o")
    plt.title(f"{LAKE_NAME} area (Sentinel-2, Oct-Nov)")
    plt.ylabel("km2")
    plt.savefig("imja_tsho_area.png", dpi=150)
    print("Saved imja_tsho_area.csv and imja_tsho_area.png")




def water_area_km2(water):
    vectors = water.reduceToVectors(geometry=AOI, scale=10, maxPixels=1e9)
    vectors = vectors.map(lambda f: f.set("area", f.geometry().area(1)))
    largest = ee.Feature(vectors.sort("area", False).first())
    return ee.Number(largest.get("area")).getInfo() / 1e6


main()
