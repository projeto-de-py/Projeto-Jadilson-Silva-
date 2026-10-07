import { cn } from '@/lib/utils';

export function Input({ className, type = 'text', ...props }) {
	return (
		<input
			type={type}
			className={cn(
				'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs',
				'placeholder:text-muted-foreground',
				'focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
				'disabled:cursor-not-allowed disabled:opacity-50',
				className,
			)}
			{...props}
		/>
	);
}
