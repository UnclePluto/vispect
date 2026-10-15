import {render,screen} from '@testing-library/react';
import {TenantEditor} from './TenantEditor';
test('机构创建表单显示三种资源额度和初始管理员',()=>{
    render(<TenantEditor open onCancel={()=>{}} onSaved={()=>{}}/>);
    expect(screen.getByLabelText('医生上限')).toBeInTheDocument();expect(screen.getByLabelText('患者上限')).toBeInTheDocument();expect(screen.getByLabelText('研究上限')).toBeInTheDocument();expect(screen.getByLabelText('管理员手机号')).toBeInTheDocument();
});
