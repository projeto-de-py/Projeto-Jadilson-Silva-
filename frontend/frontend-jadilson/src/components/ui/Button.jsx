import React from 'react';
import { cn } from '@/lib/utils';

const variants = {
	default:
		'bg-primary text-primary-foreground shadow-xs hover:bg-primary/90',
	secondary:
		'bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80',
	ghost: 'hover:bg-muted hover:text-foreground',
	outline:
		'border border-input bg-background shadow-xs hover:bg-muted hover:text-foreground',
};

const sizes = {
	default: 'h-10 px-4 py-2',
	sm: 'h-9 rounded-md px-3',
	lg: 'h-11 rounded-md px-8',
	icon: 'h-10 w-10',
};

export function Button({
	variant = 'default',
	size = 'default',
	className,
	asChild = false,
	children,
	...props
}) {
	const classes = cn(
		'inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors',
		'focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
		'disabled:pointer-events-none disabled:opacity-50',
		variants[variant],
		sizes[size],
		className,
	);

	if (asChild) {
		return React.cloneElement(children, { className: cn(classes, children.props.className) });
	}

	return (
		<button className={classes} {...props}>
			{children}
		</button>
	);
}
