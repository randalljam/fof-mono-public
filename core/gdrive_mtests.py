from core.fileops import *
from core.gdrive import *

if True:
    pass
if __name__ == "__main__":        
    cur_file_path = ""

def mtest_list_files_in_shared_drive():
    pass
if __name__ == "__main__":
    # OAuth 2.0 Playground URI that worked:
    # https://www.googleapis.com/drive/v3/files?corpora=drive&driveId=0AEvH3N5wS0EVUk9PVA&includeItemsFromAllDrives=true&supportsAllDrives=true&q='1D1YcJd_rYAj2aIye0twemh76qRm8PY4D'+in+parents&fields=files(id,name)       
    cur_shared_drive_id = '0AEvH3N5wS0EVUk9PVA'  # for FL MAIN shared drive
    cur_folder_id = '1D1YcJd_rYAj2aIye0twemh76qRm8PY4D'  # CMS Letters folder in FL MAIN
    print(list_files_in_shared_drive(cur_shared_drive_id, cur_folder_id))
def mtest_get_full_folder_path():
    pass
#if __name__ == "__main__":        
    #cur_folder_id = '1tX2bGgZBraVnhnG9j00etIexAD_Nlxbp'  # test folder in My Drive personal
    #cur_folder_id = '1HpmvR3O2G2D9zamtiVTo1VbbWaf7dd-u' # 3D print folder in My Drive personal
    cur_folder_id = '1D1YcJd_rYAj2aIye0twemh76qRm8PY4D'  # CMS Letters folder in FL MAIN
    print(get_full_folder_path(cur_folder_id, service=GDRIVE_SERVICE_FLWORKSPACE))
def mtest_list_gdrive_files():
    pass
#if __name__ == "__main__":        
    #cur_folder_id = '1tX2bGgZBraVnhnG9j00etIexAD_Nlxbp'  # test folder in My Drive personal
    #cur_folder_id = '1HpmvR3O2G2D9zamtiVTo1VbbWaf7dd-u' # 3D print folder in My Drive personal
    cur_folder_id = '1D1YcJd_rYAj2aIye0twemh76qRm8PY4D'  # CMS Letters folder in FL MAIN
    print(list_gdrive_files(cur_folder_id, service=GDRIVE_SERVICE_FLWORKSPACE))
def mtest_list_gdrive_files():
    pass
#if __name__ == "__main__":        
    cur_folder_id = '1tX2bGgZBraVnhnG9j00etIexAD_Nlxbp'
    print(list_gdrive_files_iteratively(cur_folder_id))
def mtest_create_gdrive_folder_csv():
    pass
#if __name__ == "__main__":        
    cur_folder_id = '1tX2bGgZBraVnhnG9j00etIexAD_Nlxbp'
    create_gdrive_folder_csv(cur_folder_id, 'tests/test_data_files/manual_output/gdrive_folder_test.csv')