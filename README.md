[ Description ] 

- Rename standard gateway and cluster firewalls (as well as rename cluster members). 

- Reset SIC without restarting services. 

- Perform SIC reset on gateway without restarting services and management side via API. 

- Update objects with user provided names.


[ Limitations ] 

Currently only for MDM. (Requires domain specific information) 

May not work with SMB appliances. (not tested) 


[ Usage ] 

1. Download compiled binary from dist/ and move to MDM. 

2. Execute binary. 

./gw_rename {-d} {-h}

3. Provide access information for API/MDM/Domain. 

4. Check and verify provided informaiton from script for the given gateway. 

5. Provide new names for relevant objects. 

6. Script will perform the rest of the steps. 

