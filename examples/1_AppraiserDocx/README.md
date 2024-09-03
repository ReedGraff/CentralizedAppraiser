This package is a simple example of how to use the `CentralizedAppraiser` project to generate a report in a Word document and in JSON. The Word document is a template that contains placeholders for the data that will be inserted into the report. The JSON is data representing what it collected from the county. The runner.py file will read the template, replaces the placeholders with the actual data, and generates a new report & JSON.

This package requires a google maps API key to run. You can get a key from the Google Cloud Platform Console. The key should be stored in a file called `creds.txt` in the root directory of the project.
- This key will be used to:
    - geocode the addresses
    - generate the map images in the report.

Requires the following packages:
- CentralizedAppraiser
- shapely
- json
- pyproj
- docxtpl
- docx2pdf