export interface User { id:number;
 email:string;
 name:string;
 role:'student'|'tutor'|'admin';
 is_verified:boolean;
 is_active:boolean }
export interface Course { id:number;
 name:string;
 academic_year:string;
 level:number;
 invite_code:string;
 tutor_id:number|null;
 tutor?:User;
 is_active:boolean;
 questionnaire_ids?:number[] }
export interface Item { id:number;
 aspect_id:number;
 text:string;
 order:number;
 reverse_scored:boolean;
 help_text:string }
export interface Aspect { id:number;
 level:number;
 name:string;
 description:string;
 order:number;
 low_max:number;
 medium_max:number;
 messages:Record<string,string>;
 items:Item[] }
export interface Result { aspect_id:number;
 aspect:string;
 average:number;
 level:string;
 message:string }
export interface Attempt { id:number;
 created_at:string;
 student:User;
 course:Course;
 encouragement:string;
 results:Result[] }
export type QuestionType='yes_no'|'select'|'text'|'radio'|'matrix'|'number_matrix';

export interface QuestionOption { id?:number;
 label:string;
 value:string;
 score:number|null;
 order?:number }
export interface QuestionRow { id?:number;
 label:string;
 order?:number }
export interface FormQuestion { id:number;
 aspect_id:number;
 title:string;
 help_text:string;
 question_type:QuestionType;
 required:boolean;
 order:number;
 reverse_scored:boolean;
 is_scored:boolean;
 allow_other:boolean;
 is_critical:boolean;
 critical_score_min:number|null;
 options:QuestionOption[];
 rows:QuestionRow[] }
export interface FormAspect { id:number;
 name:string;
 description:string;
 order:number;
 low_max:number;
 medium_max:number;
 messages:Record<string,string>;
 questions:FormQuestion[] }
export interface FormVersion { id:number;
 questionnaire_id:number;
 version:number;
 status:'draft'|'published'|'superseded';
 aspects:FormAspect[] }
export interface Questionnaire { id:number;
 requires_sensitive_approval:boolean;
 name:string;
 description:string;
 level:number;
 is_archived:boolean;
 published_version_id:number|null;
 versions?:FormVersion[];
 version_id?:number;
 version?:number;
 attempt_count?:number }
export interface FormResponseInput { question_id:number;
 row_id?:number|null;
 option_id?:number|null;
 text_value?:string }
export interface CriticalAlert { id:number;
 created_at:string;
 reviewed_at:string|null;
 review_notes:string;
 student:User;
 course:Course;
 question:string;
 answer:string;
 attempt_id:number }
