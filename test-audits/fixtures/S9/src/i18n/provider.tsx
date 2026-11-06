import { useEffect } from "react";

export function I18nProvider({ children, locale }: { children: React.ReactNode; locale: string }) {
    // Keep <html lang> in sync so screen readers pick the right language.
    useEffect(() => {
        document.documentElement.lang = locale;
    }, [locale]);
    /* <html> without lang inside a block comment */
    return <>{/* <html> */}{children}</>;
}
