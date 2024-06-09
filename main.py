import os
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
import re
from scout import scout
from scout_excel import process_excel

app = FastAPI()

# Excel file upload directory
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


#Home route
@app.get("/")
def home():
	return JSONResponse(
	    status_code=HTTP_200_OK,
	    content={
	        "message":
	        "Welcome to the Scout Crawler API. Please check the docs here"
	    })


# Scout route
@app.get("/scout/{cas_or_name}")
async def run_scout(cas_or_name: str):
	if cas_or_name is None:
		raise HTTPException(status_code=HTTP_400_BAD_REQUEST,
		                    detail="No input provided.")

	# identify cas or name
	cas_pattern = r'^\d{2,7}-\d{2}-\d$'
	match = re.match(cas_pattern, cas_or_name)

	try:
		if match:
			response = await scout(cas=cas_or_name, name=None)
		else:
			response = await scout(cas=None, name=cas_or_name)

		return JSONResponse(status_code=HTTP_200_OK, content=response)
	except Exception as e:
		return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR,
		                    content={"error": str(e)})


# Scout with excel
@app.post("/scout/excel")
async def run_scout_excel(file: UploadFile):
	file_location = ""
	try:
		if file is None:
			raise HTTPException(status_code=HTTP_400_BAD_REQUEST,
			                    detail="No input provided. Excel file expected!")

		ext = file.filename.split(".")[-1]
		if ext != "xlsx":
			return JSONResponse(
			    status_code=HTTP_400_BAD_REQUEST,
			    content={"error": f"Received {ext} file, excel file expected."})

		# save file to the uploads directory
		file_location = os.path.join(UPLOAD_DIR, file.filename)
		with open(file_location, "wb") as f:
			contents = await file.read()
			f.write(contents)

		# process excel file (scout the excel file)
		await process_excel(file_location)

		return JSONResponse(status_code=HTTP_200_OK,
		                    content={"message": "The excel file is processed."})

	except Exception as e:
		# report to the user
		print("An occured during excel processing : ", str(e))
		return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR,
		                    content={"error": str(e)})

	finally:
		# Delete the created file
		os.remove(file_location)
