SELECT 
	m.Sngay,  
    m.ngay_ct,  
    m.Ky_hieu,  
    m.Mau_so,  
    m.so_Ct,
    m.Sp,
    m.ID_Nx,  
    nx.Ma_Ct,  
    m.ID_kho,  
    kho.Ten_Nhom,  
    m.ID_Dt,  
    dt.Ten_Dt,  
    dt.MST,  
    M.Cong_SlQd,
    m.Cong_Sl,
    m.Tien_hang,
    m.ID_Thue,
    m.Tien_Gtgt,
    m.Tong_Tien
FROM SlNxM m  
LEFT JOIN DmNx nx ON m.ID_Nx = nx.ID  
LEFT JOIN DmNKho kho ON m.ID_kho = kho.ID  
LEFT JOIN DmDt dt ON m.ID_Dt = dt.ID  
WHERE kho.Ten_Nhom IS NOT NULL
AND m.ID_DT IS NOT NULL
and nx.Ma_Ct ='NM'
ORDER BY m.Sngay DESC;