CREATE OR REPLACE FUNCTION public.update_modified_column()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = timezone('utc', now());

    IF (TG_OP = 'INSERT') THEN
        NEW.created_at = timezone('utc', now());
    END IF;

    RETURN NEW;
END;
$function$;