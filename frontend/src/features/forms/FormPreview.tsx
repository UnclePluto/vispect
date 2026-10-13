import {Modal} from 'antd';
import {DynamicForm} from '../../form-engine/DynamicForm';
import type {FormDefinition} from '../../form-engine/types';
export function FormPreview({definition,open,onClose}:{definition:FormDefinition;open:boolean;onClose:()=>void}){return <Modal title="表单预览" open={open} onCancel={onClose} footer={null} width={760} destroyOnHidden><DynamicForm definition={definition} initialAnswers={{}} mode="preview" readOnly={false}/></Modal>}
