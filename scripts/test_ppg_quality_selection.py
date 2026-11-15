"""Kiểm quyết định chọn ứng viên: không đổi coverage lấy số giả hoặc lỗi lớn."""
from benchmark_ppg_quality import decision


def records(*,balanced_noise=None,strict_noise=None,balanced_added=80.1,strict_added=80.2):
    public = {'category':'BIDMC_ECG_HR','rows':[
        {'reference_bpm':80.,'predictions':{'current_cpp':80.,'hybrid_balanced':80.,'hybrid_strict':80.}},
        {'reference_bpm':80.,'predictions':{'current_cpp':None,'hybrid_balanced':balanced_added,'hybrid_strict':strict_added}},
    ]}
    noise = {'category':'SYNTHETIC_known_control','expected_no_pulse':True,'rows':[
        {'reference_bpm':None,'predictions':{'current_cpp':None,'hybrid_balanced':balanced_noise,'hybrid_strict':strict_noise}},
    ]}
    return [public,noise]


def main():
    chosen = decision(records(balanced_noise=73.))
    assert chosen['selected_policy']=='strict'
    assert not chosen['candidates']['balanced']['checks']['no_noise_acceptance']
    assert decision(records(balanced_noise=73.,strict_noise=73.))['selected_policy'] is None
    assert decision(records())['selected_policy']=='balanced'
    failed = decision(records(strict_added=95.))
    assert not failed['candidates']['strict']['checks']['no_additional_over10']
    assert failed['selected_policy']=='balanced'
    print('PASS: 4 selection cases (reject noise, reject all, rank declared metrics, reject added large error)')


if __name__=='__main__':
    main()
