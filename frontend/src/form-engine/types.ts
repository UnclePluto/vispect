export type JSONValue=null|boolean|number|string|JSONValue[]|{[key:string]:JSONValue};
export type QuestionType='text'|'textarea'|'number'|'date'|'radio'|'checkbox'|'select'|'slider';
export type Rule={question_id:string;operator:'eq'|'neq'|'contains'|'gt'|'gte'|'lt'|'lte'|'answered';value?:string|number|boolean};
export type Question={id:string;type:QuestionType;title:string;description?:string;required?:boolean;min_length?:number;max_length?:number;min?:number;max?:number;precision?:number;step?:number;min_selections?:number;max_selections?:number;options?:{id:string;label:string}[];condition?:{mode:'all'|'any';rules:Rule[]};jumps?:Record<string,string>};
export type FormDefinition={protocol_version:1;title:string;description?:string;questions:Question[]};
export type EvaluationResult={visible_ids:string[];answers:Record<string,JSONValue>;errors:Record<string,string[]>};
